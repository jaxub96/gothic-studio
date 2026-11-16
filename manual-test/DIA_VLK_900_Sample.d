// Dialog file for Sample (VLK_900_Sample)
// Hand-written on purpose: custom helpers, variables, shared menus, odd styles.

var int Sample_Flag;
var int Sample_Counter;

func void B_Sample_Helper()
{
	Sample_Counter += 1;
};

// ------------------------------------------------------------
instance DIA_Sample_Hallo (C_INFO)
{
	npc			= VLK_900_Sample;
	nr			= 5;
	condition	= DIA_Sample_Hallo_Cond;
	information	= DIA_Sample_Hallo_Run;
	permanent	= 0;
	description	= "Czeœæ, co s³ychaæ?";
};
func int DIA_Sample_Hallo_Cond ()
{
	return TRUE;
};
func void DIA_Sample_Hallo_Run ()
{
	AI_Output (other, self, "DIA_Sample_Hallo_15_00"); //Czeœæ, co s³ychaæ?
	AI_Output (self, other, "DIA_Sample_Hallo_10_01"); //Dobrze ciê widzieæ.
	Sample_Flag = TRUE;
	B_Sample_Helper();
	Info_ClearChoices (DIA_Sample_Hallo);
	Info_AddChoice (DIA_Sample_Hallo, "Potrzebujê pomocy.", DIA_Sample_Hallo_Help);
	Info_AddChoice (DIA_Sample_Hallo, "Okradnê ciê.", DIA_Sample_Hallo_Steal);
};
func void DIA_Sample_Hallo_Help ()
{
	AI_Output (other, self, "DIA_Sample_Hallo_Help_15_00"); //Potrzebujê pomocy.
	AI_Output (self, hero, "DIA_Sample_Hallo_Help_10_01"); //WeŸ to.
	CreateInvItems (self, ItMi_Gold, 50);
	B_GiveInvItems (self, other, ItMi_Gold, 50);
	B_GivePlayerXP (XP_Ambient);
	Info_ClearChoices (DIA_Sample_Hallo);
};
func void DIA_Sample_Hallo_Steal ()
{
	AI_Output (self, other, "DIA_Sample_Hallo_Steal_10_00"); //Spróbuj tylko.
	Info_AddChoice (DIA_Sample_Hallo, "Jednak nie.", DIA_Sample_Hallo_Back);
};
func void DIA_Sample_Hallo_Back ()
{
	Info_ClearChoices (DIA_Sample_Pickpocket);
	Info_ClearChoices (DIA_Sample_Hallo);
};

// ------------------------------------------------------------
instance DIA_Sample_Quest (C_INFO)
{
	npc			= VLK_900_Sample;
	nr			= 6;
	condition	= DIA_Sample_Quest_Cond;
	information	= DIA_Sample_Quest_Run;
	permanent	= 0;
	description	= "Masz dla mnie zadanie?";
};
func int DIA_Sample_Quest_Cond ()
{
	if (Sample_Flag == TRUE)			//ordered: flag first ...
	&& (Npc_KnowsInfo (other, DIA_Sample_Hallo))	//... then knowledge ...
	&& (Kapitel >= 2)					//... then chapter
	{
		return TRUE;
	};
};
func void DIA_Sample_Quest_Run ()
{
	AI_Output (other, self, "DIA_Sample_Quest_15_00"); //Masz dla mnie zadanie?
	AI_Output (self, other, "DIA_Sample_Quest_10_01"); //ZnajdŸ mojego kuriera.
	Log_CreateTopic (TOPIC_Sample, LOG_MISSION);
	Log_SetTopicStatus (TOPIC_Sample, LOG_RUNNING);
	B_LogEntry (TOPIC_Sample, "Mam znaleŸæ kuriera.");
	Npc_ExchangeRoutine (self, "Guide");
	Wld_InsertNpc (Sample_Courier, "WP_SAMPLE");
	B_StartOtherRoutine (Sample_Guard, "ALERT");
	if (Sample_Counter > 0)
	{
		AI_Output (self, other, "DIA_Sample_Quest_10_02"); //Ju¿ raz mi pomog³eœ.
	}
	else
	{
		AI_Output (self, other, "DIA_Sample_Quest_10_03"); //Pierwszy raz, prawda?
	};
	AI_StopProcessInfos (self);
};

// ------------------------------------------------------------
// This one is on purpose odd: an Info function that returns int.
// Studio cannot write that back unchanged, so it must be kept as written.
instance DIA_Sample_Legacy (C_INFO)
{
	npc			= VLK_900_Sample;
	nr			= 7;
	condition	= DIA_Sample_Legacy_Cond;
	information	= DIA_Sample_Legacy_Run;
	permanent	= 1;
	description	= "Stara sprawa";
};
func int DIA_Sample_Legacy_Cond () { return TRUE; };
func int DIA_Sample_Legacy_Run ()
{
	AI_Output (self, other, "DIA_Sample_Legacy_10_00"); //Stare dzieje.
	return 1;
};
