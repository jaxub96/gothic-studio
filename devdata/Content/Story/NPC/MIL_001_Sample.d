instance MIL_001_Sample (Npc_Default)
{
	name	= "Sample";
	B_SetNpcVisual (self, MALE, "HUM_HEAD_PONY", Face_N_Player, BodyTex_N, ITAR_Mil_L);
	Mdl_ApplyOverlayMds (self, "HUMANS_MILITIA.MDS");
	Mdl_ApplyOverlayMds (self, "HUMANS_RELAXED.MDS");
	Mdl_ApplyOverlayMds (self, "HUMANS_TIRED.MDS");
	// "HUM_HEAD_BALD" "HUM_HEAD_FIGHTER" "HUM_HEAD_THIEF" "HUM_HEAD_PSIONIC"
};
