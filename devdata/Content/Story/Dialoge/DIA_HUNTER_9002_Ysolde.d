// Dialog file for Ysolde (HUNTER_9002_Ysolde)
// Sample: a dialog that only exists while another NPC's quest runs, and a
// permanent one that stays until the hero can pay.

// ============================================================
// 					EXIT
// ============================================================
instance DIA_HUNTER_9002_Ysolde_EXIT (C_INFO)
{
	npc			= HUNTER_9002_Ysolde;
	nr			= 999;
	condition	= DIA_HUNTER_9002_Ysolde_EXIT_Condition;
	information	= DIA_HUNTER_9002_Ysolde_EXIT_Info;
	permanent	= 1;
	description = DIALOG_ENDE;
};

FUNC int DIA_HUNTER_9002_Ysolde_EXIT_Condition()
{
	return 1;
};

FUNC VOID DIA_HUNTER_9002_Ysolde_EXIT_Info()
{
	AI_StopProcessInfos	(self);
};

// ============================================================
// 			Have you seen a courier?
// ============================================================
instance DIA_HUNTER_9002_Ysolde_Courier (C_INFO)
{
	npc			= HUNTER_9002_Ysolde;
	nr			= 1;
	condition	= DIA_HUNTER_9002_Ysolde_Courier_Condition;
	information	= DIA_HUNTER_9002_Ysolde_Courier_Info;
	permanent	= 0;
	description	= "Have you seen a courier on the road?";
};

FUNC int DIA_HUNTER_9002_Ysolde_Courier_Condition()
{
	return MIS_Mod_LostOrders == LOG_RUNNING;
};

FUNC VOID DIA_HUNTER_9002_Ysolde_Courier_Info()
{
	AI_Output (other, self,"DIA_HUNTER_9002_Ysolde_Courier_15_00"); //Have you seen a courier on the road?
	AI_Output (self, other,"DIA_HUNTER_9002_Ysolde_Courier_16_01"); //What was left of him. Wolves got there before I did.
	AI_Output (self, other,"DIA_HUNTER_9002_Ysolde_Courier_16_02"); //He had a letter on him. Sealed. Looks important - and important things are worth something.
	B_LogEntry	(TOPIC_Mod_LostOrders,"The courier is dead. The hunter Ysolde has his orders and wants paying for them.");
};

// ============================================================
// 			Here is your gold
// ============================================================
instance DIA_HUNTER_9002_Ysolde_Pay (C_INFO)
{
	npc			= HUNTER_9002_Ysolde;
	nr			= 2;
	condition	= DIA_HUNTER_9002_Ysolde_Pay_Condition;
	information	= DIA_HUNTER_9002_Ysolde_Pay_Info;
	permanent	= 1;
	description	= "(Pay 50 gold for the orders)";
};

FUNC int DIA_HUNTER_9002_Ysolde_Pay_Condition()
{
	return Npc_KnowsInfo (other, DIA_HUNTER_9002_Ysolde_Courier) && Npc_HasItems (self, ItMi_Mod_SealedOrders) >= 1;
};

FUNC VOID DIA_HUNTER_9002_Ysolde_Pay_Info()
{
	AI_Output (other, self,"DIA_HUNTER_9002_Ysolde_Pay_15_00"); //Here's your gold.
	if (B_GiveInvItems (other, self, ItMi_Gold, MOD_INFORMANT_FEE))
	{
		AI_Output (self, other,"DIA_HUNTER_9002_Ysolde_Pay_16_01"); //Pleasure doing business.
		B_GiveInvItems (self, hero, ItMi_Mod_SealedOrders, 1);
		B_GivePlayerXP(XP_Mod_Found);
	}
	else
	{
		AI_Output (self, other,"DIA_HUNTER_9002_Ysolde_Pay_16_02"); //That is not 50 gold. Come back when you have it.
	};
};
