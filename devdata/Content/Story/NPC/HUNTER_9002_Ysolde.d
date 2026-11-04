instance HUNTER_9002_Ysolde (Npc_Default)
{
	// ---------------- primary ----------------
	name			= "Ysolde";
	guild			= GIL_HUNTER;
	id				= 9002;
	voice			= 16;
	flags			= 0;
	npctype			= NPCTYPE_AMBIENT;

	// ---------------- attributes ----------------
	level			= 12;
	attribute[ATR_STRENGTH]		= 35;
	attribute[ATR_DEXTERITY]	= 70;
	attribute[ATR_MANA_MAX]		= 0;
	attribute[ATR_MANA]			= 0;
	attribute[ATR_HITPOINTS_MAX]= 160;
	attribute[ATR_HITPOINTS]	= 160;

	// ---------------- visuals ----------------
	B_SetNpcVisual		(self, FEMALE, "HUM_HEAD_BABE8", 140, 5, ITAR_BauBabe_L);
	Mdl_ApplyOverlayMds	(self, "HUMANS_BABE.MDS");
	Mdl_SetModelFatness	(self, 0);

	// ---------------- fight ----------------
	fight_tactic	= FAI_HUMAN_NORMAL;
	B_SetFightSkills	(self, 30);
	Npc_SetTalentSkill	(self, NPC_TALENT_BOW, 2);

	// ---------------- inventory ----------------
	CreateInvItems	(self, ItRw_Arrow, 30);
	CreateInvItems	(self, ItFo_Mod_SmokedEel, 2);
	CreateInvItems	(self, ItMi_Mod_SealedOrders, 1);

	// ---------------- talents ----------------
	Npc_SetTalentSkill	(self, NPC_TALENT_SNEAK, 1);
	Npc_SetTalentSkill	(self, NPC_TALENT_TAKEANIMALTROPHY, 1);

	daily_routine	= Rtn_9002_Ysolde_01;
};

FUNC VOID Rtn_9002_Ysolde_01()
{
	TA_Sit_Campfire	(06,00,23,00,"NW_FOREST_PATH_04_16_MONSTER");
	TA_Sleep	(23,00,06,00,"NW_FOREST_PATH_04_16_MONSTER");
};
