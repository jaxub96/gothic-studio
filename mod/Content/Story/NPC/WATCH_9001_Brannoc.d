instance WATCH_9001_Brannoc (Npc_Default)
{
	// ---------------- primary ----------------
	name			= "Brannoc";
	guild			= GIL_WATCH;
	id				= 9001;
	voice			= 8;
	flags			= NPC_FLAG_IMMORTAL;
	npctype			= NPCTYPE_MAIN;

	// ---------------- attributes ----------------
	level			= 20;
	attribute[ATR_STRENGTH]		= 90;
	attribute[ATR_DEXTERITY]	= 40;
	attribute[ATR_MANA_MAX]		= 0;
	attribute[ATR_MANA]			= 0;
	attribute[ATR_HITPOINTS_MAX]= 280;
	attribute[ATR_HITPOINTS]	= 280;

	// ---------------- visuals ----------------
	B_SetNpcVisual		(self, MALE, "HUM_HEAD_FIGHTER", Face_N_Important_Arto, BodyTex_N, ITAR_Mil_M);
	Mdl_ApplyOverlayMds	(self, "HUMANS_MILITIA.MDS");
	Mdl_SetModelFatness	(self, 1);

	// ---------------- fight ----------------
	fight_tactic	= FAI_HUMAN_STRONG;
	B_SetFightSkills	(self, 60);
	Npc_SetTalentSkill	(self, NPC_TALENT_1H, 2);
	Npc_SetTalentSkill	(self, NPC_TALENT_CROSSBOW, 1);

	// ---------------- inventory ----------------
	CreateInvItems	(self, ItMw_Mod_WatchSword, 1);
	CreateInvItems	(self, ITAR_Mod_Watch_L, 1);
	CreateInvItems	(self, ItMi_Gold, 120);
	B_CreateAmbientInv	(self);

	daily_routine	= Rtn_9001_Brannoc_01;
};

FUNC VOID Rtn_9001_Brannoc_01()
{
	TA_Stand_Guarding	(07,00,22,00,"NW_CITY_ENTRANCE_01");
	TA_Sleep	(22,00,07,00,"NW_CITY_HABOUR_KASERN_05_01");
};
