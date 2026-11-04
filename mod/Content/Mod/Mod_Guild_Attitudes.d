// ============================================================================
//  MOD GUILD ATTITUDES
// ============================================================================
//
//  How the guilds feel about each other: who attacks whom on sight, who just
//  grumbles, who looks the other way. The hero takes the attitudes of the
//  guild they join.
//
//      ATT_HOSTILE   attack on sight
//      ATT_ANGRY     warn, then attack if provoked
//      ATT_NEUTRAL   ignore
//      ATT_FRIENDLY  help in a fight
//
//  Wld_SetGuildAttitude (a, att, b) sets one direction only - write both lines
//  when the feeling is mutual. Anything not listed keeps vanilla's value.
//
//  Call B_Mod_InitGuildAttitudes() right after B_InitGuildAttitudes() in
//  every INIT_<world> in Story/Startup.d, so these win. install.py does it.
// ============================================================================

func void B_Mod_SetMutualAttitude (var int a, var int att, var int b)
{
	Wld_SetGuildAttitude (a, att, b);
	Wld_SetGuildAttitude (b, att, a);
};

func void B_Mod_InitGuildAttitudes ()
{
	// --- Law and order: the Watch and the Flame stand together ---------------
	B_Mod_SetMutualAttitude (GIL_WATCH,		ATT_FRIENDLY,	GIL_FLAME);
	B_Mod_SetMutualAttitude (GIL_WATCH,		ATT_FRIENDLY,	GIL_CITIZEN);
	B_Mod_SetMutualAttitude (GIL_WATCH,		ATT_ANGRY,		GIL_FREEBLADE);	// rivals, not enemies
	B_Mod_SetMutualAttitude (GIL_WATCH,		ATT_HOSTILE,	GIL_CORSAIR);
	B_Mod_SetMutualAttitude (GIL_WATCH,		ATT_HOSTILE,	GIL_CONVICT);

	// --- The monastery keeps out of politics ------------------------------
	B_Mod_SetMutualAttitude (GIL_FIRECIRCLE,	ATT_FRIENDLY,	GIL_ACOLYTE);
	B_Mod_SetMutualAttitude (GIL_FIRECIRCLE,	ATT_NEUTRAL,	GIL_TIDECIRCLE);
	B_Mod_SetMutualAttitude (GIL_FIRECIRCLE,	ATT_FRIENDLY,	GIL_FLAME);

	// --- The countryside ------------------------------------------------
	B_Mod_SetMutualAttitude (GIL_FREEBLADE,	ATT_FRIENDLY,	GIL_FARMER);
	B_Mod_SetMutualAttitude (GIL_HUNTER,		ATT_NEUTRAL,	GIL_FARMER);
	B_Mod_SetMutualAttitude (GIL_HUNTER,		ATT_NEUTRAL,	GIL_CORSAIR);	// they trade furs for rum

	// --- Everybody's enemies ---------------------------------------------
	B_Mod_SetMutualAttitude (GIL_BRIGAND,	ATT_HOSTILE,	GIL_WATCH);
	B_Mod_SetMutualAttitude (GIL_BRIGAND,	ATT_HOSTILE,	GIL_FARMER);
	B_Mod_SetMutualAttitude (GIL_BRIGAND,	ATT_HOSTILE,	GIL_HUNTER);
	B_Mod_SetMutualAttitude (GIL_SHADOWCULT,	ATT_HOSTILE,	GIL_WATCH);
	B_Mod_SetMutualAttitude (GIL_SHADOWCULT,	ATT_HOSTILE,	GIL_FLAME);
	B_Mod_SetMutualAttitude (GIL_SHADOWCULT,	ATT_HOSTILE,	GIL_FIRECIRCLE);
	B_Mod_SetMutualAttitude (GIL_SHADOWCULT,	ATT_HOSTILE,	GIL_TIDECIRCLE);
	B_Mod_SetMutualAttitude (GIL_SHADOWCULT,	ATT_HOSTILE,	GIL_SLAYER);
};
