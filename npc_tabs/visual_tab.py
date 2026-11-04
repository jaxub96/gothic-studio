"""Visual tab - appearance, with live texture previews.

B_SetNpcVisual(self, gender, headMesh, faceTex, bodyTex, armor) is the Gothic 2
call. It takes no teeth or skin-colour argument, so those controls are gone -
the old tool collected them and fed them to Mdl_SetNpcVisual, which does not
exist in Gothic 2 at all.

The face and body pickers show the actual texture, because
"Face_N_Tough_Bartholo" tells you nothing on its own.
"""

from PyQt6.QtWidgets import QVBoxLayout, QWidget

import gamedata
import labels
import textures
import ui
from texture_view import FACE_CROP, TexturePanel


def build(parent: QWidget, npc, handlers) -> None:
    """Build the tab, and rebuild it whenever the gender changes.

    Women and men are offered different head meshes, faces, skins, walks and
    voices, so the lists cannot be fixed at build time. Switching gender swaps
    in the other set, and any value that does not belong to it is replaced by
    the first one that does.
    """
    outer = parent.layout()
    outer.setContentsMargins(0, 0, 0, 0)
    state = {"gender": None, "inner": None, "previews": lambda: None}

    def populate():
        if state["inner"] is not None:
            outer.removeWidget(state["inner"])
            state["inner"].deleteLater()
        inner = QWidget()
        inner.setLayout(QVBoxLayout())
        outer.addWidget(inner)
        state["inner"] = inner
        state["gender"] = npc.gender
        state["previews"] = _fill(inner.layout(), npc, handlers)

    def adopt_gender():
        """Move the NPC's visuals onto the new gender's lists."""
        g = npc.gender
        if npc.head not in gamedata.heads_for(g):
            npc.head = gamedata.heads_for(g)[0]
        if npc.face not in gamedata.faces_for(g):
            npc.face = gamedata.faces_for(g)[0]
        if npc.body_tex not in gamedata.body_textures_for(g):
            npc.body_tex = gamedata.body_textures_for(g)[0]
        # Women walk the female way unless chosen otherwise afterwards.
        if (g == "FEMALE" and gamedata.FEMALE_WALK in gamedata.overlays_for(g)) \
                or npc.overlay not in gamedata.overlays_for(g):
            npc.overlay = gamedata.overlays_for(g)[0]
        if int(npc.voice) not in gamedata.voices_for(g):
            npc.voice = gamedata.voices_for(g)[0]

    def refresh_previews():
        if npc.gender != state["gender"]:
            adopt_gender()
            populate()
            handlers.refresh()          # the script and 3D view follow
            return
        state["previews"]()

    populate()
    parent.refresh_previews = refresh_previews


def _fill(layout, npc, handlers):
    """The tab's widgets for npc.gender. Returns the function that re-syncs
    the texture previews."""
    layout.setSpacing(0)
    layout.setContentsMargins(ui.SPACING, ui.SPACING, ui.SPACING, ui.SPACING)
    gender = npc.gender

    face_values = gamedata.face_values()
    body_values = gamedata.body_texture_values()

    ui.section(layout, "Preview")
    previews = ui.row(ui.SPACING)
    face_panel = TexturePanel("Face", height=124, crop=FACE_CROP)
    body_panel = TexturePanel("Skin", height=124)
    previews.addWidget(face_panel)
    previews.addWidget(body_panel)
    previews.addStretch()
    layout.addLayout(previews)
    layout.addSpacing(ui.SPACING)

    def refresh_previews():
        fv = face_values.get(npc.face)
        face_panel.show_texture(
            textures.face_texture(fv) if fv is not None else None,
            f"{npc.face}  (V{fv})" if fv is not None else npc.face)
        bv = body_values.get(npc.body_tex)
        body_panel.show_texture(
            textures.body_texture(bv) if bv is not None else None,
            f"{npc.body_tex}  (V{bv})" if bv is not None else npc.body_tex)

    def setter(attr):
        def apply(shown):
            value = labels.raw(shown)
            if value:
                handlers.assignAttribute(attr, lambda: value)
                refresh_previews()
        return apply

    ui.section(layout, "Appearance")

    # Only heads with a real name. The rest are internal variants nobody can
    # tell apart by their constant - but keep the NPC's own head if it is one,
    # so opening a vanilla NPC does not silently change it.
    heads = [h for h in gamedata.heads_for(gender) if h in labels.HEAD]
    if npc.head and npc.head.upper() not in heads:
        heads.append(npc.head.upper())
    ui.field(layout, "Head mesh",
             ui.dropdown(labels.label_list(labels.HEAD, heads),
                         labels.pretty(labels.HEAD, npc.head), setter("head")))

    faces = gamedata.faces_for(gender)
    ui.field(layout, "Face",
             ui.search_dropdown(faces, npc.face, setter("face")),
             f'{len(faces)} faces, in the game\'s own order. Type to search'
             + ('.' if gender == "FEMALE" else ', e.g. "Thorus".'))

    ui.field(layout, "Skin",
             ui.dropdown(labels.label_list(labels.BODY, gamedata.body_textures_for(gender)),
                         labels.pretty(labels.BODY, npc.body_tex),
                         setter("body_tex")))

    ui.field(layout, "Walk style",
             ui.dropdown(labels.label_list(labels.OVERLAY, gamedata.overlays_for(gender)),
                         labels.pretty(labels.OVERLAY, npc.overlay),
                         setter("overlay")))

    ui.field(layout, "Voice",
             ui.dropdown([str(v) for v in gamedata.voices_for(gender)], str(npc.voice),
                         lambda t: handlers.assignAttribute(
                             "voice", lambda: t, int)),
             "Which SVM speech set this character uses.")

    # The one place a slider belongs: a continuous shape you judge by eye,
    # with the model updating as you drag.
    ui.field(layout, "Build",
             ui.slider(-100, 200, int(npc.fatness * 100),
                       lambda v: handlers.assignAttribute(
                           "fatness", lambda: v / 100.0, float),
                       fmt=lambda v: f"{v / 100.0:+.2f}"),
             "Thinner to heavier. Everything else here is a fixed choice.")

    layout.addStretch()
    refresh_previews()
    # The page re-syncs us when the model changes from elsewhere (e.g. armor
    # picked on the Inventory tab, or a loaded NPC).
    return refresh_previews
