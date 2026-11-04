// Dialog file for Varn (CORSAIR_9003_Varn)
// Sample: a trader. `trade = 1` opens the trade screen with whatever is in
// his inventory (see CreateInvItems in his NPC file).

// ============================================================
// 					EXIT
// ============================================================
instance DIA_CORSAIR_9003_Varn_EXIT (C_INFO)
{
	npc			= CORSAIR_9003_Varn;
	nr			= 999;
	condition	= DIA_CORSAIR_9003_Varn_EXIT_Condition;
	information	= DIA_CORSAIR_9003_Varn_EXIT_Info;
	permanent	= 1;
	description = DIALOG_ENDE;
};

FUNC int DIA_CORSAIR_9003_Varn_EXIT_Condition()
{
	return 1;
};

FUNC VOID DIA_CORSAIR_9003_Varn_EXIT_Info()
{
	AI_StopProcessInfos	(self);
};

// ============================================================
// 			Who are you?
// ============================================================
instance DIA_CORSAIR_9003_Varn_Who (C_INFO)
{
	npc			= CORSAIR_9003_Varn;
	nr			= 1;
	condition	= DIA_CORSAIR_9003_Varn_Who_Condition;
	information	= DIA_CORSAIR_9003_Varn_Who_Info;
	permanent	= 0;
	description	= "Who are you?";
};

FUNC int DIA_CORSAIR_9003_Varn_Who_Condition()
{
	return 1;
};

FUNC VOID DIA_CORSAIR_9003_Varn_Who_Info()
{
	AI_Output (other, self,"DIA_CORSAIR_9003_Varn_Who_15_00"); //Who are you?
	AI_Output (self, other,"DIA_CORSAIR_9003_Varn_Who_06_01"); //A humble importer of fish. And other things the Watch has no need to hear about.
	Log_CreateTopic	(TOPIC_Mod_Traders, LOG_NOTE);
	B_LogEntry	(TOPIC_Mod_Traders,"Varn sells food and tinctures at the harbour tavern.");
	B_GivePlayerXP(XP_Mod_Talk);
};

// ============================================================
// 			Show me your wares
// ============================================================
instance DIA_CORSAIR_9003_Varn_Trade (C_INFO)
{
	npc			= CORSAIR_9003_Varn;
	nr			= 2;
	condition	= DIA_CORSAIR_9003_Varn_Trade_Condition;
	information	= DIA_CORSAIR_9003_Varn_Trade_Info;
	permanent	= 1;
	description	= "Show me your wares.";
	trade		= 1;
};

FUNC int DIA_CORSAIR_9003_Varn_Trade_Condition()
{
	return Npc_KnowsInfo (other, DIA_CORSAIR_9003_Varn_Who);
};

FUNC VOID DIA_CORSAIR_9003_Varn_Trade_Info()
{
	AI_Output (other, self,"DIA_CORSAIR_9003_Varn_Trade_15_00"); //Show me your wares.
};
