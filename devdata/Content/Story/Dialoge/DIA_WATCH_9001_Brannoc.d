// Dialog file for Brannoc (WATCH_9001_Brannoc)
// Sample: a quest giver who also lets the hero join a guild.
//
//   Hello       important - he speaks first
//   LostOrders  starts TOPIC_Mod_LostOrders (MIS_Mod_LostOrders = LOG_RUNNING)
//   OrdersDone  only while the quest runs and the hero carries the orders
//   JoinNotYet  asked too early: what the hero still has to do
//   Join        level MOD_WATCH_MIN_LEVEL and the quest done: join GIL_WATCH
//
// AI_Output ids follow vanilla: <info>_<speaker voice>_<line>, 15 is the hero.

// ============================================================
// 					EXIT
// ============================================================
instance DIA_WATCH_9001_Brannoc_EXIT (C_INFO)
{
	npc			= WATCH_9001_Brannoc;
	nr			= 999;
	condition	= DIA_WATCH_9001_Brannoc_EXIT_Condition;
	information	= DIA_WATCH_9001_Brannoc_EXIT_Info;
	permanent	= 1;
	description = DIALOG_ENDE;
};

FUNC int DIA_WATCH_9001_Brannoc_EXIT_Condition()
{
	return 1;
};

FUNC VOID DIA_WATCH_9001_Brannoc_EXIT_Info()
{
	AI_StopProcessInfos	(self);
};

// ============================================================
// 			Hello
// ============================================================
instance DIA_WATCH_9001_Brannoc_Hello (C_INFO)
{
	npc			= WATCH_9001_Brannoc;
	nr			= 1;
	condition	= DIA_WATCH_9001_Brannoc_Hello_Condition;
	information	= DIA_WATCH_9001_Brannoc_Hello_Info;
	permanent	= 0;
	important	= 1;
};

FUNC int DIA_WATCH_9001_Brannoc_Hello_Condition()
{
	return 1;
};

FUNC VOID DIA_WATCH_9001_Brannoc_Hello_Info()
{
	AI_Output (self, other,"DIA_WATCH_9001_Brannoc_Hello_08_00"); //You there. New in town?
	AI_Output (other, self,"DIA_WATCH_9001_Brannoc_Hello_15_01"); //Just off the ferry.
	AI_Output (self, other,"DIA_WATCH_9001_Brannoc_Hello_08_02"); //Then hear the rules. No blades drawn inside the walls, no thieving, and no trouble with the Watch.
	AI_Output (self, other,"DIA_WATCH_9001_Brannoc_Hello_08_03"); //Keep to that and we will get along.
};

// ============================================================
// 			I'm looking for work
// ============================================================
instance DIA_WATCH_9001_Brannoc_LostOrders (C_INFO)
{
	npc			= WATCH_9001_Brannoc;
	nr			= 2;
	condition	= DIA_WATCH_9001_Brannoc_LostOrders_Condition;
	information	= DIA_WATCH_9001_Brannoc_LostOrders_Info;
	permanent	= 0;
	description	= "I'm looking for work.";
};

FUNC int DIA_WATCH_9001_Brannoc_LostOrders_Condition()
{
	return Npc_KnowsInfo (other, DIA_WATCH_9001_Brannoc_Hello);
};

FUNC VOID DIA_WATCH_9001_Brannoc_LostOrders_Info()
{
	AI_Output (other, self,"DIA_WATCH_9001_Brannoc_LostOrders_15_00"); //I'm looking for work.
	AI_Output (self, other,"DIA_WATCH_9001_Brannoc_LostOrders_08_01"); //A courier never arrived from the farms. He was carrying sealed orders for me.
	AI_Output (self, other,"DIA_WATCH_9001_Brannoc_LostOrders_08_02"); //The hunters in the forest see everything on that road. Ask them.
	MIS_Mod_LostOrders = LOG_RUNNING;
	Log_CreateTopic	(TOPIC_Mod_LostOrders, LOG_MISSION);
	Log_SetTopicStatus	(TOPIC_Mod_LostOrders, LOG_RUNNING);
	B_LogEntry	(TOPIC_Mod_LostOrders,"Brannoc of the Watch is missing a courier with sealed orders. The hunters in the forest may know more.");
};

// ============================================================
// 			I have your orders
// ============================================================
instance DIA_WATCH_9001_Brannoc_OrdersDone (C_INFO)
{
	npc			= WATCH_9001_Brannoc;
	nr			= 3;
	condition	= DIA_WATCH_9001_Brannoc_OrdersDone_Condition;
	information	= DIA_WATCH_9001_Brannoc_OrdersDone_Info;
	permanent	= 0;
	description	= "I have your orders.";
};

FUNC int DIA_WATCH_9001_Brannoc_OrdersDone_Condition()
{
	return MIS_Mod_LostOrders == LOG_RUNNING && Npc_HasItems (other, ItMi_Mod_SealedOrders) >= 1;
};

FUNC VOID DIA_WATCH_9001_Brannoc_OrdersDone_Info()
{
	AI_Output (other, self,"DIA_WATCH_9001_Brannoc_OrdersDone_15_00"); //I have your orders.
	B_GiveInvItems (other, self, ItMi_Mod_SealedOrders, 1);
	AI_Output (self, other,"DIA_WATCH_9001_Brannoc_OrdersDone_08_01"); //The seal is whole. Good work - here, you have earned this.
	CreateInvItems(self, ItMi_Gold, 150);
	B_GiveInvItems (self, hero, ItMi_Gold, 150);
	MIS_Mod_LostOrders = LOG_SUCCESS;
	Mod_Rep_Watch = Mod_Rep_Watch + 5;
	Log_SetTopicStatus	(TOPIC_Mod_LostOrders, LOG_SUCCESS);
	B_LogEntry	(TOPIC_Mod_LostOrders,"I brought Brannoc his orders.");
	B_GivePlayerXP(XP_Mod_QuestMedium);
};

// ============================================================
// 			I want to join the Watch (not ready yet)
// ============================================================
instance DIA_WATCH_9001_Brannoc_JoinNotYet (C_INFO)
{
	npc			= WATCH_9001_Brannoc;
	nr			= 4;
	condition	= DIA_WATCH_9001_Brannoc_JoinNotYet_Condition;
	information	= DIA_WATCH_9001_Brannoc_JoinNotYet_Info;
	permanent	= 1;
	description	= "I want to join the Watch.";
};

FUNC int DIA_WATCH_9001_Brannoc_JoinNotYet_Condition()
{
	return hero.guild == GIL_NONE && Npc_KnowsInfo (other, DIA_WATCH_9001_Brannoc_Hello)
		&& (other.level < MOD_WATCH_MIN_LEVEL || MIS_Mod_LostOrders != LOG_SUCCESS);
};

FUNC VOID DIA_WATCH_9001_Brannoc_JoinNotYet_Info()
{
	AI_Output (other, self,"DIA_WATCH_9001_Brannoc_JoinNotYet_15_00"); //I want to join the Watch.
	AI_Output (self, other,"DIA_WATCH_9001_Brannoc_JoinNotYet_08_01"); //Not so fast. The Watch takes no green recruits, and no strangers.
	AI_Output (self, other,"DIA_WATCH_9001_Brannoc_JoinNotYet_08_02"); //Get some experience, and show me you can be trusted.
	Log_CreateTopic	(TOPIC_Mod_JoinWatch, LOG_NOTE);
	B_LogEntry	(TOPIC_Mod_JoinWatch,"Brannoc will take me into the Watch once I am experienced enough and have done him a service.");
};

// ============================================================
// 			I want to join the Watch
// ============================================================
//  Only one of JoinNotYet / Join is ever offered: their conditions are opposites.
instance DIA_WATCH_9001_Brannoc_Join (C_INFO)
{
	npc			= WATCH_9001_Brannoc;
	nr			= 4;
	condition	= DIA_WATCH_9001_Brannoc_Join_Condition;
	information	= DIA_WATCH_9001_Brannoc_Join_Info;
	permanent	= 1;
	description	= "I want to join the Watch.";
};

FUNC int DIA_WATCH_9001_Brannoc_Join_Condition()
{
	return hero.guild == GIL_NONE && Npc_KnowsInfo (other, DIA_WATCH_9001_Brannoc_Hello)
		&& other.level >= MOD_WATCH_MIN_LEVEL && MIS_Mod_LostOrders == LOG_SUCCESS;
};

FUNC VOID DIA_WATCH_9001_Brannoc_Join_Info()
{
	Info_ClearChoices	(DIA_WATCH_9001_Brannoc_Join);
	AI_Output (other, self,"DIA_WATCH_9001_Brannoc_Join_15_00"); //I want to join the Watch.
	AI_Output (self, other,"DIA_WATCH_9001_Brannoc_Join_08_01"); //You have proved yourself. Are you ready to swear the oath?
	Info_AddChoice	(DIA_WATCH_9001_Brannoc_Join,"Not yet.",DIA_WATCH_9001_Brannoc_Join_Later);
	Info_AddChoice	(DIA_WATCH_9001_Brannoc_Join,"I swear it.",DIA_WATCH_9001_Brannoc_Join_Swear);
};

func void DIA_WATCH_9001_Brannoc_Join_Swear()
{
	AI_Output (other, self,"DIA_WATCH_9001_Brannoc_Join_Swear_15_00"); //I swear it.
	AI_Output (self, other,"DIA_WATCH_9001_Brannoc_Join_Swear_08_01"); //Then you are one of us. Wear these with pride.
	hero.guild = GIL_WATCH;
	Npc_SetTrueGuild (hero, GIL_WATCH);
	CreateInvItems(self, ITAR_Mod_Watch_L, 1);
	B_GiveInvItems (self, hero, ITAR_Mod_Watch_L, 1);
	B_LogEntry	(TOPIC_Mod_JoinWatch,"I have joined the City Watch.");
	B_GivePlayerXP(XP_Mod_JoinGuild);
	Info_ClearChoices	(DIA_WATCH_9001_Brannoc_Join);
};

func void DIA_WATCH_9001_Brannoc_Join_Later()
{
	AI_Output (other, self,"DIA_WATCH_9001_Brannoc_Join_Later_15_00"); //Not yet.
	AI_Output (self, other,"DIA_WATCH_9001_Brannoc_Join_Later_08_01"); //The offer stands.
	Info_ClearChoices	(DIA_WATCH_9001_Brannoc_Join);
};
