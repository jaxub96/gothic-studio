"""
model_view.py - the 3D character preview.

Renders the NPC as it will look in game: body or armor mesh, head mesh on the
head bone, wearing the chosen face and skin textures.

Controls
    drag left           turn and tilt
    drag right/middle   pan
    wheel               zoom
    F / B / L / R       front, back, left, right
    Home                reset the view
    W                   wireframe
    T                   textures on/off

Three things keep it responsive:
  * assembled meshes and decoded textures are cached, so turning the figure is
    only a redraw - no re-parsing, no re-decoding;
  * redraws are skipped unless a field that changes the look moved, so typing
    a name costs nothing;
  * dragging renders to a fixed small pixel budget - so it stays smooth even
    on a maximised window - and snaps back to full detail on release.
"""

from PyQt6.QtCore import QSize, Qt, QTimer
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import QLabel, QSizePolicy, QVBoxLayout, QWidget

import render3d
import ui
from theme import THEME

FRONT = 180.0            # the meshes face away from the camera at yaw 0
MIN_ZOOM, MAX_ZOOM = 0.35, 8.0

#: While dragging, render roughly this many pixels regardless of how big the
#: panel is, so turning the figure stays smooth on a maximised window.
DRAG_TARGET_PIXELS = 55_000
VIEWS = {"F": (180, "Front"), "B": (0, "Back"), "L": (90, "Left"), "R": (270, "Right")}


class _Canvas(QLabel):
    """Just the picture. Separate so it can own the mouse and keyboard."""

    def __init__(self, owner):
        super().__init__()
        self.owner = owner
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(160, 200)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setStyleSheet(ui.image_frame(0).styleSheet())
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def sizeHint(self):
        return QSize(360, 520)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.owner.on_resize()

    def mousePressEvent(self, e):
        self.owner.begin_drag(e)

    def mouseMoveEvent(self, e):
        self.owner.drag(e)

    def mouseReleaseEvent(self, e):
        self.owner.end_drag(e)

    def wheelEvent(self, e):
        self.owner.zoom_by(1.0015 ** e.angleDelta().y())

    def keyPressEvent(self, e):
        if not self.owner.handle_key(e.key()):
            super().keyPressEvent(e)


class ModelView(QWidget):
    def __init__(self, npc, parent=None):
        super().__init__(parent)
        self.npc = npc
        self.yaw = FRONT
        self.pitch = 6.0
        self.zoom = 1.0
        self.pan = [0.0, 0.0]
        self.wireframe = False
        self.textured = True

        self._drag = None
        self._last_key = None
        self._models = None

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(160)
        self._timer.timeout.connect(lambda: self.render_now())

        self._resize_timer = QTimer(self)
        self._resize_timer.setSingleShot(True)
        self._resize_timer.setInterval(120)
        self._resize_timer.timeout.connect(lambda: self.render_now())

        col = QVBoxLayout(self)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(4)

        self.canvas = _Canvas(self)
        self.canvas.setText("building...")
        self.canvas.setToolTip(
            "Drag to turn, right-drag to pan, wheel to zoom.  "
            "F / B / L / R for views, Home resets, "
            "W wireframe, T textures.")
        col.addWidget(self.canvas, stretch=1)

    def _turn_left(self):
        self.turn(-45)

    def _turn_right(self):
        self.turn(45)

    # ------------------------------------------------------------ interaction
    def _set_flag(self, attr, value):
        setattr(self, attr, value)
        self.render_now()

    def turn(self, delta):
        self.yaw = (self.yaw + delta) % 360
        self.render_now()

    def set_yaw(self, angle):
        self.yaw = angle % 360
        self.render_now()

    def zoom_by(self, factor):
        self.zoom = max(MIN_ZOOM, min(MAX_ZOOM, self.zoom * factor))
        self.render_now(scale=self._drag_scale())
        self._timer.start(140)

    def reset_view(self):
        self.yaw, self.pitch, self.zoom = FRONT, 6.0, 1.0
        self.pan = [0.0, 0.0]
        self.render_now()

    def handle_key(self, key):
        actions = {
            Qt.Key.Key_F: lambda: self.set_yaw(180),
            Qt.Key.Key_B: lambda: self.set_yaw(0),
            Qt.Key.Key_L: lambda: self.set_yaw(90),
            Qt.Key.Key_R: lambda: self.set_yaw(270),
            Qt.Key.Key_Home: self.reset_view,
            Qt.Key.Key_Plus: lambda: self.zoom_by(1.25),
            Qt.Key.Key_Equal: lambda: self.zoom_by(1.25),
            Qt.Key.Key_Minus: lambda: self.zoom_by(1 / 1.25),
            Qt.Key.Key_W: lambda: self._set_flag("wireframe", not self.wireframe),
            Qt.Key.Key_T: lambda: self._set_flag("textured", not self.textured),
        }
        action = actions.get(key)
        if action:
            action()
            return True
        return False

    def begin_drag(self, event):
        self._drag = (event.position().x(), event.position().y(), event.button())
        self.canvas.setCursor(Qt.CursorShape.ClosedHandCursor)

    def drag(self, event):
        if not self._drag:
            return
        x, y, button = self._drag
        dx = event.position().x() - x
        dy = event.position().y() - y
        self._drag = (event.position().x(), event.position().y(), button)

        if button == Qt.MouseButton.LeftButton:
            self.yaw = (self.yaw + dx * 0.8) % 360
            self.pitch = max(-89.0, min(89.0, self.pitch - dy * 0.4))
        else:
            self.pan[0] += dx
            self.pan[1] += dy
        self.render_now(scale=self._drag_scale())

    def end_drag(self, _event):
        self._drag = None
        self.canvas.setCursor(Qt.CursorShape.OpenHandCursor)
        self.render_now()

    def _drag_scale(self):
        """Shrink the drag frame to a fixed pixel budget, never enlarge it."""
        area = self.canvas.size()
        pixels = max(1, area.width() * area.height())
        return min(1.0, (DRAG_TARGET_PIXELS / pixels) ** 0.5)

    def on_resize(self):
        self._resize_timer.start()

    # -------------------------------------------------------------- redrawing
    def _look_key(self):
        n = self.npc
        return (n.armor, n.head, n.face, n.body_tex, n.gender)

    def mark_stale(self):
        """The model changed while we were hidden; redraw when shown again."""
        self._last_key = None
        self._models = None

    def refresh(self):
        key = self._look_key()
        if key == self._last_key:
            return
        self._last_key = key
        self._models = None
        self._timer.start()

    def _get_models(self):
        if self._models is None:
            self._models = render3d.character(self.npc)
        return self._models

    def render_now(self, scale=1.0):
        self._timer.stop()
        area = self.canvas.size()
        w = max(64, int(area.width() * scale))
        h = max(64, int(area.height() * scale))
        try:
            models = self._get_models()
            image = render3d.render(
                models, w, h, yaw=self.yaw, pitch=self.pitch,
                background=_rgb(THEME["bg_code"]),
                zoom=self.zoom, pan=(self.pan[0] * scale, self.pan[1] * scale),
                wireframe=self.wireframe, textured=self.textured)
        except Exception as exc:                     # never take the app down
            self.canvas.setPixmap(QPixmap())
            self.canvas.setText("preview unavailable: " + str(exc)[:80])
            return

        if not image:
            self.canvas.setPixmap(QPixmap())
            self.canvas.setText("no mesh found")
            return

        iw, ih, rgb = image
        qimg = QImage(rgb, iw, ih, iw * 3, QImage.Format.Format_RGB888).copy()
        pm = QPixmap.fromImage(qimg)
        if scale != 1.0:
            pm = pm.scaled(area, Qt.AspectRatioMode.KeepAspectRatio,
                           Qt.TransformationMode.FastTransformation)
        self.canvas.setPixmap(pm)

        # No caption: the picture is the point, and the controls are on the
        # mouse, the keyboard and the canvas tooltip.


def _rgb(hex_color):
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
