// ============================================================================
//  MOD CONSTANTS
// ============================================================================
//
//  Numbers the mod's scripts share. Change a value here and every NPC,
//  dialog and item that uses the name follows. Only `const` and `var` lines
//  live in this file, so it can load as early as you like.
//
//  Values are in the same range as vanilla Gothic II, so the balance feels
//  familiar: a chapter-1 quest is worth 100-300 XP, a militia sword costs
//  a few hundred gold, a guild wants you around level 5 before it takes you.
//
//  Loaded right after Mod_Guilds.d (see mod/README.md).
// ============================================================================

// --- NPC ids --------------------------------------------------------------
//  Vanilla NPCs use ids up to ~1500. Keep the mod's in a block of their own so
//  an id never says "which NPC" twice. Gothic Studio's NPC id field takes these.
const int MOD_NPC_ID_FIRST		= 9000;
const int MOD_NPC_ID_LAST		= 9999;

// --- Experience -----------------------------------------------------------
//  B_GivePlayerXP (XP_...). Gothic Studio lists every XP_ constant it finds.
const int XP_Mod_Talk			= 25;		// learned something by talking
const int XP_Mod_Found			= 50;		// found a hidden thing
const int XP_Mod_QuestSmall		= 100;		// errand
const int XP_Mod_QuestMedium	= 250;		// a proper quest
const int XP_Mod_QuestBig		= 500;		// a chapter's main quest
const int XP_Mod_JoinGuild		= 300;		// accepted into a guild

// --- Joining a guild --------------------------------------------------------
const int MOD_WATCH_MIN_LEVEL		= 5;
const int MOD_ACOLYTE_TRIBUTE		= 1000;	// gold, like vanilla's monastery fee
const int MOD_FREEBLADE_MIN_LEVEL	= 5;

// --- Prices (gold) --------------------------------------------------------
const int MOD_PRICE_ROOM			= 30;	// one night at the tavern
const int MOD_PRICE_FERRY			= 50;
const int MOD_BRIBE_WATCH			= 100;	// make a crime go away
const int MOD_INFORMANT_FEE			= 50;

// --- Teaching costs (learning points) ----------------------------------------
//  Vanilla charges 1 LP per attribute point at the bottom of the scale and
//  more as it climbs; one combat-talent percent costs 1-3 LP.
const int MOD_LP_ATTRIBUTE_CHEAP	= 1;
const int MOD_LP_ATTRIBUTE_DEAR		= 2;
const int MOD_LP_SNEAK				= 5;
const int MOD_LP_PICKLOCK			= 10;

// --- Reputation -----------------------------------------------------------
//  How much each faction likes the hero. 0 is a stranger; dialogs check these.
var int Mod_Rep_Watch;
var int Mod_Rep_Farmers;
var int Mod_Rep_Corsairs;

const int MOD_REP_TRUSTED			= 10;
const int MOD_REP_HATED				= -10;

// --- Quest states -----------------------------------------------------------
//  One var per quest, holding LOG_RUNNING / LOG_SUCCESS / LOG_FAILED / LOG_OBSOLETE
//  - the same pattern as vanilla's MIS_* vars. 0 means not started.
var int MIS_Mod_LostOrders;
