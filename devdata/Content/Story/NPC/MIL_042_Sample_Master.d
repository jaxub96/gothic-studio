instance MIL_042_Sample_Master (Npc_Default)
{
	// ---------------- primary ----------------
	name			= "Sample Master";
	guild			= GIL_MIL;
	id				= 042;
	voice			= 3;
	flags			= NPC_FLAG_IMMORTAL;
	npctype			= NPCTYPE_FRIEND;

	// ---------------- attributes ----------------
	level			= 20;
	attribute[ATR_STRENGTH]		= 80;
	attribute[ATR_DEXTERITY]	= 65;
	attribute[ATR_MANA_MAX]		= 30;
	attribute[ATR_MANA]			= 30;
	attribute[ATR_HITPOINTS_MAX]= 320;
	attribute[ATR_HITPOINTS]	= 320;

	// ---------------- visuals ----------------
	B_SetNpcVisual		(self, MALE, "HUM_HEAD_BALD", Face_N_Gomez, BodyTex_P, ITAR_Mil_M);
	Mdl_ApplyOverlayMds	(self, "HUMANS_MILITIA.MDS");
	Mdl_SetModelFatness	(self, 0.5);

	// ---------------- fight ----------------
	fight_tactic	= FAI_HUMAN_MASTER;
	B_SetFightSkills	(self, 20);
	Npc_SetTalentSkill	(self, NPC_TALENT_1H, 2);
	Npc_SetTalentSkill	(self, NPC_TALENT_2H, 1);
	Npc_SetTalentSkill	(self, NPC_TALENT_BOW, 2);
	Npc_SetTalentSkill	(self, NPC_TALENT_CROSSBOW, 1);
	Npc_SetTalentSkill	(self, NPC_TALENT_MAGE, 3);

	// ---------------- inventory ----------------
	CreateInvItems	(self, ItMi_Gold, 250);
	CreateInvItems	(self, ItFo_Apple, 3);
	CreateInvItems	(self, ItFo_Bread, 2);
	CreateInvItems	(self, ItPo_Health_01, 4);
	CreateInvItems	(self, ItMw_1H_Sword_01, 1);
	CreateInvItems	(self, ItRw_Arrow, 40);
	CreateInvItems	(self, ItKe_Lockpick, 5);
	B_CreateAmbientInv	(self);

	// ---------------- talents ----------------
	Npc_SetTalentSkill	(self, NPC_TALENT_ALCHEMY, 1);
	Npc_SetTalentSkill	(self, NPC_TALENT_RUNES, 1);
	Npc_SetTalentSkill	(self, NPC_TALENT_SMITH, 1);
	Npc_SetTalentSkill	(self, NPC_TALENT_TAKEANIMALTROPHY, 1);
	Npc_SetTalentSkill	(self, NPC_TALENT_PICKLOCK, 1);
	Npc_SetTalentSkill	(self, NPC_TALENT_PICKPOCKET, 1);
	Npc_SetTalentSkill	(self, NPC_TALENT_SNEAK, 1);
	Npc_SetTalentSkill	(self, NPC_TALENT_ACROBAT, 1);
	Npc_SetTalentSkill	(self, NPC_TALENT_REGENERATE, 1);
	Npc_SetTalentSkill	(self, NPC_TALENT_FIREMASTER, 1);
	Npc_SetTalentSkill	(self, NPC_TALENT_FOREIGNLANGUAGE, 1);
	Npc_SetTalentSkill	(self, NPC_TALENT_WISPDETECTOR, 1);

	daily_routine	= Rtn_042_Sample_Master_01;
};

FUNC VOID Rtn_042_Sample_Master_01()
{
	TA_Smith_Anvil	(07,00,21,00,"WP_CITY_SQUARE");
	TA_Sleep	(21,00,07,00,"WP_PASS_ENTRANCE");
};
