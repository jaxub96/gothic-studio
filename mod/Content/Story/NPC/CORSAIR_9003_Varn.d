instance CORSAIR_9003_Varn (Npc_Default)
{
	// ---------------- primary ----------------
	name			= "Varn";
	guild			= GIL_CORSAIR;
	id				= 9003;
	voice			= 6;
	flags			= 0;
	npctype			= NPCTYPE_MAIN;

	// ---------------- attributes ----------------
	level			= 15;
	attribute[ATR_STRENGTH]		= 55;
	attribute[ATR_DEXTERITY]	= 50;
	attribute[ATR_MANA_MAX]		= 0;
	attribute[ATR_MANA]			= 0;
	attribute[ATR_HITPOINTS_MAX]= 210;
	attribute[ATR_HITPOINTS]	= 210;

	// ---------------- visuals ----------------
	B_SetNpcVisual		(self, MALE, "HUM_HEAD_PONY", Face_P_Tough_Torrez, BodyTex_P, ITAR_PIR_M_Addon);
	Mdl_ApplyOverlayMds	(self, "HUMANS_ARROGANCE.MDS");
	Mdl_SetModelFatness	(self, 0);

	// ---------------- fight ----------------
	fight_tactic	= FAI_HUMAN_STRONG;
	B_SetFightSkills	(self, 45);
	Npc_SetTalentSkill	(self, NPC_TALENT_1H, 1);

	// ---------------- inventory ----------------
	CreateInvItems	(self, ItMi_Gold, 300);
	CreateInvItems	(self, ItFo_Mod_SmokedEel, 6);
	CreateInvItems	(self, ItPo_Mod_Tincture, 4);
	CreateInvItems	(self, ItFo_Beer, 5);

	daily_routine	= Rtn_9003_Varn_01;
};

FUNC VOID Rtn_9003_Varn_01()
{
	TA_Stand_Drinking	(08,00,23,00,"NW_CITY_HABOUR_TAVERN01_01");
	TA_Sit_Bench	(23,00,08,00,"NW_CITY_HABOUR_TAVERN01_01");
};
