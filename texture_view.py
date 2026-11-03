"""
texture_view.py - Qt side of the texture previews.

textures.py turns a .TEX into raw pixels; this turns those into something you
can look at while picking a face, body or armor.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget

import textures
import ui
from theme import THEME

# A head texture is a UV sheet: the face sits in the middle, ears and the back
# of the head wrap around the edges. Cropping to the middle gives a portrait
# instead of a smear. Measured against HUM_HEAD_V*_C0.
FACE_CROP = (0.22, 0.0, 0.78, 1.0)


def _to_pixmap(decoded, crop=None):
    """(w, h, rgb888) -> QPixmap, optionally cropped to a relative box."""
    if not decoded:
        return None
    w, h, rgb = decoded
    image = QImage(rgb, w, h, w * 3, QImage.Format.Format_RGB888)
    # QImage does not copy the buffer, and `rgb` is a local - copy before it dies.
    image = image.copy()
    if crop:
        x0, y0, x1, y1 = crop
        image = image.copy(int(w * x0), int(h * y0),
                           max(1, int(w * (x1 - x0))), max(1, int(h * (y1 - y0))))
    return QPixmap.fromImage(image)


def pixmap(ref, crop=None, height=128):
    pm = _to_pixmap(textures.decode(ref), crop)
    if pm is None:
        return None
    return pm.scaledToHeight(height, Qt.TransformationMode.SmoothTransformation)


class TexturePanel(QWidget):
    """A labelled thumbnail that degrades honestly to 'no preview'."""

    def __init__(self, title, height=128, crop=None, parent=None):
        super().__init__(parent)
        self._height = height
        self._crop = crop

        col = QVBoxLayout(self)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(3)

        self.title = ui.heading(title)

        self.image = ui.image_frame(height)

        self.caption = ui.hint("")

        col.addWidget(self.title)
        col.addWidget(self.image)
        col.addWidget(self.caption)

    def show_texture(self, ref, caption=""):
        pm = pixmap(ref, self._crop, self._height) if ref else None
        if pm is None:
            self.image.setPixmap(QPixmap())
            self.image.setText("no preview")
            self.caption.setText(caption or "not in this install's textures")
        else:
            self.image.setPixmap(pm)
            self.caption.setText(caption or getattr(ref, "name", ""))

    def clear(self):
        self.image.setPixmap(QPixmap())
        self.image.setText("-")
        self.caption.setText("")
