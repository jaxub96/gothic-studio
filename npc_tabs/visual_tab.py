"""Visual tab - appearance, with live texture previews.

B_SetNpcVisual(self, gender, headMesh, faceTex, bodyTex, armor) is the Gothic 2
call. It takes no teeth or skin-colour argument, so those controls are gone -
the old tool collected them and fed them to Mdl_SetNpcVisual, which does not
exist in Gothic 2 at all.

The face and body pickers show the actual texture, because
"Face_N_Tough_Bartholo" tells you nothing on its own.
"""

from PyQt6.QtWidgets import QWidget

import gamedata
import labels
import textures
import ui
from texture_view import FACE_CROP, TexturePanel


def build(parent: QWidget, npc, handlers) -> None:
    layout = parent.layout()
    layout.setSpacing(0)
    layout.setContentsMargins(ui.SPACING, ui.SPACING, ui.SPACING, ui.SPACING)

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

    ui.field(layout, "Head mesh",
             ui.dropdown(labels.label_list(labels.HEAD, gamedata.heads()),
                         labels.pretty(labels.HEAD, npc.head), setter("head")))

    faces = gamedata.faces()
    ui.field(layout, "Face",
             ui.search_dropdown(faces, npc.face, setter("face")),
             f'{len(faces)} faces, in the game\'s own order. Type to search, e.g. "Thorus".')

    ui.field(layout, "Skin",
             ui.dropdown(labels.label_list(labels.BODY, gamedata.body_textures()),
                         labels.pretty(labels.BODY, npc.body_tex),
                         setter("body_tex")))

    ui.field(layout, "Walk style",
             ui.dropdown(labels.label_list(labels.OVERLAY, gamedata.overlays()),
                         labels.pretty(labels.OVERLAY, npc.overlay),
                         setter("overlay")))

    ui.field(layout, "Voice",
             ui.dropdown([str(v) for v in gamedata.voices()], str(npc.voice),
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
    # Let the page re-sync us when the model changes from elsewhere
    # (e.g. armor picked on the Inventory tab, or a loaded NPC).
    parent.refresh_previews = refresh_previews
