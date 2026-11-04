// ============================================================================
//  MOD GUILDS
// ============================================================================
//
//  The engine gives humans 16 guild slots, numbered 0..15 in
//  _intern/Constants.d. Vanilla Gothic II already uses every one of them
//  (15 is GIL_PUBLIC, the owner of public rooms), and its scripts test those
//  names everywhere - B_GetPlayerCrime, the guild armors, Npc_IsPlayer checks,
//  the attitude table. So a mod does not add guilds; it TAKES OVER a slot.
//
//  Each line below gives a vanilla slot the name your own scripts use for it.
//  Vanilla code keeps working (it still says GIL_MIL), and everything you write
//  says GIL_WATCH. Retire a slot you do not need and you have a free one.
//
//  Format - Gothic Studio reads the name after // for its guild picker:
//
//      const int GIL_<YOURNAME> = GIL_<VANILLA SLOT>;   // Display name - note
//
//  What the PLAYER sees (the status screen, "Guild: ...") comes from
//  TXT_GUILDS in Text.d. When you rename a guild here, rename it there too.
//
//  Loaded right after _intern\Constants.d (see mod/README.md).
// ============================================================================

// --- The town -----------------------------------------------------------------
const int GIL_WATCH			= GIL_MIL;		// City Watch - the harbour town's guards; joinable
const int GIL_FLAME			= GIL_PAL;		// Order of the Flame - knights; Watch members can rise into it
const int GIL_CITIZEN		= GIL_VLK;		// Citizen - merchants, craftsmen, dock workers

// --- The monastery ------------------------------------------------------------
const int GIL_FIRECIRCLE	= GIL_KDF;		// Circle of Fire - mages of the monastery
const int GIL_ACOLYTE		= GIL_NOV;		// Acolyte - monastery novices; joinable

// --- The countryside -------------------------------------------------------
const int GIL_FREEBLADE		= GIL_SLD;		// Freeblade - mercenaries hired by the farmers; joinable
const int GIL_FARMER		= GIL_BAU;		// Farmer - landowners and their hands
const int GIL_HUNTER		= GIL_OUT;		// Hunter - trappers who live in the woods

// --- Outsiders -------------------------------------------------------------
const int GIL_TIDECIRCLE	= GIL_KDW;		// Tide Circle - mages who guard the old ruins
const int GIL_CORSAIR		= GIL_PIR;		// Corsair - smugglers in the hidden cove
const int GIL_BRIGAND		= GIL_BDT;		// Brigand - highway robbers, hostile to all
const int GIL_CONVICT		= GIL_STRF;		// Convict - prisoners in the mine
const int GIL_SLAYER		= GIL_DJG;		// Slayer - monster hunters for hire
const int GIL_SHADOWCULT	= GIL_DMT;		// Shadow Cult - the enemy; hostile to all

// GIL_NONE (0) and GIL_PUBLIC (15) stay as they are.
