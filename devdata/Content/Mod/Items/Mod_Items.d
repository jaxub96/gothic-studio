// ============================================================================
//  MOD ITEMS
// ============================================================================
//
//  One of each kind of item, laid out the way vanilla Gothic II writes them,
//  so you can copy the nearest one and change it. Every number sits in a
//  constant at the top - balance lives in one place.
//
//  Visuals are borrowed from vanilla items; a new model only needs a new
//  visual = "...3DS" line. The armor reuses the militia mesh and texture.
//
//  Loaded after vanilla's Items and before Story\NPC (see mod/README.md),
//  because NPC inventories and dialogs name these instances.
// ============================================================================

// --- Balance ----------------------------------------------------------------
const int Value_Mod_WatchSword			= 200;
const int Damage_Mod_WatchSword			= 40;
const int Range_Mod_WatchSword			= 100;
const int Condition_Mod_WatchSword		= 25;	// strength needed

const int Value_ITAR_Mod_Watch_L		= 500;
const int Prot_ITAR_Mod_Watch_L			= 30;	// edge, blunt and point alike

const int Value_Mod_SmokedEel			= 12;
const int HP_Mod_SmokedEel				= 15;

const int Value_Mod_Tincture			= 60;
const int HP_Mod_Tincture				= 80;
const int Mana_Mod_Tincture				= 20;


// --- Weapon -----------------------------------------------------------------
INSTANCE ItMw_Mod_WatchSword (C_Item)
{
	name 				=	"Watchman's Sword";

	mainflag 			=	ITEM_KAT_NF;
	flags 				=	ITEM_SWD;
	material 			=	MAT_METAL;

	value 				=	Value_Mod_WatchSword;

	damageTotal			= 	Damage_Mod_WatchSword;
	damagetype			=	DAM_EDGE;
	range    			=  	Range_Mod_WatchSword;

	cond_atr[2]   		= 	ATR_STRENGTH;
	cond_value[2]  		= 	Condition_Mod_WatchSword;
	visual 				=	"ItMw_025_1h_Mil_Sword_broad_01.3DS";

	description			= name;
	TEXT[2]				= NAME_Damage;			COUNT[2]	= damageTotal;
	TEXT[3] 			= NAME_Str_needed;		COUNT[3]	= cond_value[2];
	TEXT[4] 			= NAME_OneHanded;
	TEXT[5]				= NAME_Value;			COUNT[5]	= value;
};


// --- Armor ------------------------------------------------------------------
//  ITAR_<guild tag>_<weight>: Gothic Studio groups armors by that tag.
INSTANCE ITAR_Mod_Watch_L (C_Item)
{
	name 					=	"Watchman's Leathers";

	mainflag 				=	ITEM_KAT_ARMOR;
	flags 					=	0;

	protection [PROT_EDGE]	=	Prot_ITAR_Mod_Watch_L;
	protection [PROT_BLUNT] = 	Prot_ITAR_Mod_Watch_L;
	protection [PROT_POINT] = 	Prot_ITAR_Mod_Watch_L;
	protection [PROT_FIRE] 	= 	0;
	protection [PROT_MAGIC] = 	0;

	value 					=	Value_ITAR_Mod_Watch_L;

	wear 					=	WEAR_TORSO;

	visual 					=	"ItAr_Mil_L.3ds";
	visual_change 			=	"Armor_Mil_L.asc";
	visual_skin 			=	0;
	material 				=	MAT_LEATHER;

	description				=	name;
	TEXT[1]					=	NAME_Prot_Edge;		COUNT[1]	= protection[PROT_EDGE];
	TEXT[2]					=	NAME_Prot_Point;	COUNT[2]	= protection[PROT_POINT];
	TEXT[3] 				=	NAME_Prot_Fire;		COUNT[3]	= protection[PROT_FIRE];
	TEXT[4]					=	NAME_Prot_Magic;	COUNT[4]	= protection[PROT_MAGIC];
	TEXT[5]					=	NAME_Value;			COUNT[5]	= value;
};


// --- Food -------------------------------------------------------------------
INSTANCE ItFo_Mod_SmokedEel (C_Item)
{
	name 				=	"Smoked Eel";

	mainflag 			=	ITEM_KAT_FOOD;
	flags 				=	ITEM_MULTI;

	value 				=	Value_Mod_SmokedEel;

	visual 				=	"ItFo_Fish.3DS";
	material 			=	MAT_LEATHER;
	scemeName			=	"FOODHUGE";
	on_state[0]			=	Use_Mod_SmokedEel;

	description			= 	name;
	TEXT[1]				= 	NAME_Bonus_HP;		COUNT[1]	= HP_Mod_SmokedEel;
	TEXT[5]				= 	NAME_Value;			COUNT[5]	= value;
};

FUNC VOID Use_Mod_SmokedEel ()
{
	Npc_ChangeAttribute (self, ATR_HITPOINTS, HP_Mod_SmokedEel);
};


// --- Potion -----------------------------------------------------------------
INSTANCE ItPo_Mod_Tincture (C_Item)
{
	name 				=	"Herbalist's Tincture";

	mainflag 			=	ITEM_KAT_POTIONS;
	flags 				=	ITEM_MULTI;

	value 				=	Value_Mod_Tincture;

	visual 				=	"ItPo_Health_01.3ds";
	material 			=	MAT_GLAS;
	on_state[0]			=	Use_Mod_Tincture;
	scemeName			=	"POTIONFAST";

	wear				= 	WEAR_EFFECT;
	effect				=	"SPELLFX_ITEMGLIMMER";

	description			= 	name;
	TEXT[1]				= 	NAME_Bonus_HP;		COUNT[1]	= HP_Mod_Tincture;
	TEXT[2]				= 	NAME_Bonus_Mana;	COUNT[2]	= Mana_Mod_Tincture;
	TEXT[5]				= 	NAME_Value;			COUNT[5]	= value;
};

FUNC VOID Use_Mod_Tincture ()
{
	Npc_ChangeAttribute (self, ATR_HITPOINTS, HP_Mod_Tincture);
	Npc_ChangeAttribute (self, ATR_MANA, Mana_Mod_Tincture);
};


// --- Quest item -------------------------------------------------------------
//  ITEM_MISSION: cannot be sold or dropped by accident.
INSTANCE ItMi_Mod_SealedOrders (C_Item)
{
	name 				=	"Sealed Orders";

	mainflag 			=	ITEM_KAT_DOCS;
	flags 				=	ITEM_MISSION;

	value 				=	0;

	visual 				=	"ItWr_Scroll_02.3DS";
	material 			=	MAT_LEATHER;

	description			= 	name;
	TEXT[2]				= 	"A courier's dispatch for the Watch.";
	TEXT[3]				= 	"The wax seal is unbroken.";
};
