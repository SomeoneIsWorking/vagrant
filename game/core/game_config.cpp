// game_config.cpp — the Vagrant Story (SLUS_010.40, USA) GameConfig: the guest-address literals the
// PSX-generic framework reads through `c->cfg->field`.
//
// READ THIS BEFORE FILLING ANYTHING IN.
//
// **Every address in this file is ZERO, because none has been reverse-engineered in this repo.** That
// is the honest value and it is deliberate: psxport fails fast on a zero it needs, whereas a
// plausible-looking WRONG address does not fail cleanly — it breaks boot or diverges the byte-compare
// in a way that reads as a framework bug. Each group names the open step in docs/re-frontier.md.
//
// A CC0 matching decompilation of this exact executable exists and names 813 symbols in it
// (external/rood-reverse, docs/references.md; its SLUS_010.40 target is byte-identical to the image
// this repo extracts — verified 21/21 modules by tools/verify_decomp_targets.py). It is therefore an
// excellent way to LOCATE a value fast. It is NOT a substitute for measuring one: a value copied out
// of it is a REFERENCE until this repo has confirmed it against these bytes, and the standing rule in
// this workspace is that where a reference and a measurement disagree, the measurement wins. When you
// fill a field, paste the disassembly line that justifies it, as spider1/game/core/game_config.cpp
// does — that citation is what makes the value reviewable a year from now.
#include "game_iface.h"

// MEASURED, from the PS-EXE header of the extracted SLUS_010.40 (tools/extract_exe.py prints it) and
// from the disc's SYSTEM.CNF. Kept as named constants rather than dropped into the struct below,
// because the struct's boot group is consumed AS A GROUP by the framework's crt0_setup: a lone entry
// PC beside a zeroed BSS range would make it run a wrong crt0 instead of refusing.
//
//   PS-X EXE  pc0 = 0x8001F544   text = 0x80010000 + 0x52000   sp = 0x801FFFF0   gp0 = 0 (crt0 sets gp)
//   SYSTEM.CNF  BOOT = cdrom:\SLUS_010.40;1   STACK = 801fff00   TCB = 4   EVENT = 16
//
// RE-01 is exactly the step that turns these into the boot group.
static constexpr uint32_t kPsExeEntry     = 0x8001F544u;   // header pc0
static constexpr uint32_t kPsExeTextAddr  = 0x80010000u;   // header t_addr
static constexpr uint32_t kPsExeTextSize  = 0x00052000u;   // header t_size
static_assert(kPsExeEntry >= kPsExeTextAddr &&
              kPsExeEntry < kPsExeTextAddr + kPsExeTextSize,
              "the PS-EXE entry must lie inside the loaded text — if this fires, the header was "
              "misread and every number in this file's comment block is suspect");

// DESIGNATED initialisers, deliberately. GameConfig is initialised POSITIONALLY by the older
// consumers in this workspace, and the framework appends fields to it — which means a positional list
// silently re-binds every value after an inserted field. Binding by name makes an upstream insert a
// no-op here and an upstream RENAME a compile error naming the field, which is the signal we want.
// C++20 requires designators in declaration order; keep them so when adding one.
static const GameConfig g_vagrant_cfg = {
    // --- crt0 / boot ------------------------------------------------------------- RE-01, NOT DONE --
    // Left zero. See the constants above for what IS measured.
    .bssZeroLo = 0, .bssZeroHi = 0,
    .stackTopBase = 0, .stackTopBase2 = 0,
    .heapBase = 0,
    .heapSizePtr = 0, .heapBasePtr = 0,
    .gp = 0,
    .libcInit = 0,
    .gameMain = 0, .crt0 = 0,

    // --- recompiled MAIN .text range (physical) ---------------------------------- RE-02, NOT DONE --
    // These come from the RECOMPILER's own generated/overlay_table.h (REC_MAIN_LO / REC_MAIN_HI) so
    // they can never drift from the substrate they describe. There is no substrate yet, so they are
    // zero and this file does not #include that header — including a generated header that does not
    // exist would make the tree un-configurable rather than honestly incomplete.
    .recMainLo = 0, .recMainHi = 0,

    // --- disc key ----------------------------------------------- this port's own env name, not RE --
    // Not an RE fact but a port fact, and it belongs here because the framework must not know it: the
    // resolver used to hardcode the FIRST consumer's variable, so a second port set its own key,
    // nothing read it, and every boot ran with NO MEDIA behind an ordinary-looking log.
    // tools/resolve_disc.py implements the same key on the host side.
    .discEnvVar = "PSXPORT_VAGRANT_DISC",

    // --- boot intro movies ------------------------------------------- deliberately EMPTY, and why --
    // Not a gap. The framework's native .STR player only plays what a port ASKS it to play, and this
    // port asks for nothing: there is no native boot here yet, so any movie is the GUEST's to play on
    // the substrate. The disc does carry MOV/*.STR files; naming one here without knowing which the
    // boot plays would be a guess wearing a citation.
    .bootFmv = { nullptr, nullptr, nullptr, nullptr },

    // --- per-frame OT / packet pool ---------------------------------------------- RE-05, NOT DONE --
    .otRegionBase = 0, .otRegionStride = 0,
    .packetPoolBase = 0, .packetPoolStride = 0,
    .otBasePtr = 0,
    .dwellCounter = 0,
    .poolPtrCur = 0, .poolPtrLast = 0,
    .clearOtagR = 0, .putDrawEnv = 0, .drawSync = 0,
    .irqEventClasses = {0, 0, 0},
    .dualviewRenderOrch = 0, .dualviewSubmit = 0,

    // --- scheduler task layout ------------------------------- N/A until a native frame loop exists --
    // The framework's PcScheduler is not wired for this port: GameHooks' scheduler entries are
    // fail-fast stubs, so these values would have no reader even if they were known.
    .taskTableBase = 0, .taskSlotStride = 0, .taskCount = 0,
    .curTaskPtr = 0,
    .stageStart = 0, .stageDemo = 0, .stageGame = 0,

    // --- overlay router slots ---------------------------------------------------- RE-03, NOT DONE --
    // This game HAS overlay modules — 21 .PRG files on the disc (BATTLE, TITLE, ENDING, INITBTL,
    // SCREFF2 and 16 MENU/*). Their load bases are NOT known here. An overlay is keyed BY its load
    // address, so a wrong base emits a whole module of correctly-decoded instructions at wrong
    // addresses and every jal target, pointer test and router lookup is then silently wrong.
    // rood-reverse's splat configs state a vram per module; treat that as the hypothesis to CONFIRM,
    // never as the value to ship. Zero here means the router has no slot, which is what a port with
    // no recompiled overlays should say.
    .overlaySlots = { {0, nullptr}, {0, nullptr}, {0, nullptr} },

    // --- CD chokepoints ---------------------------------------------------------- RE-04, NOT DONE --
    .cdInit = 0, .cdCommand = 0, .cdSync = 0, .cdReadPrim = 0, .cdFileLoad = 0, .cdAsyncRead = 0,
    .voicePlay = 0, .voiceStop = 0, .lastSectorTracker = 0,
    .cdInlineLoad = 0,
    .cdCmdStream = 0,
    .cdCallbackTable = {0, 0, 0, 0},
    .cdCallbackFn = {0, 0, 0, 0},
    .cdGetSector = 0,
    .cdReadyCbPtr = 0,
    .cdLastPosBuf = 0,
    .cdReadStock = 0, .cdReadSync = 0,
    .cdSearchFile = 0,
    .dmaCallbackTable = 0,

    // --- pad driver -------------------------------------------------------------- RE-06, NOT DONE --
    .padSlot0Buf = 0, .padSlot1Buf = 0, .padDriverFn = 0,
    .padSlotPtrTable = 0,
    .padSlotPtrStride = 0,

    // --- platform HLE (the hardware-sync primitives) ----------------------------- RE-01, NOT DONE --
    // ZERO MEANS "not RE'd, install nothing". initBuiltins() then registers no handler and says so;
    // a run that needs one hangs in the guest's real spin loop, which is the honest signal that the RE
    // is outstanding. The windows are zero too, so register_() refuses everything — this game has not
    // stated its memory map yet, and a window guessed from another game's map is how a handler lands
    // on an unrelated function.
    .hle = {},

    // --- rendering policy ------------------------------------------------- 1 while the guest draws --
    // The renderer clears to black on the principle "show ONLY what a native producer submitted".
    // That is right for a port whose native renderer owns the frame and WRONG for one still running
    // the guest's drawing code, where an upload into the display area IS visible on real hardware:
    // logo screens, FMV stills and menus that are uploads with no primitives render black. This port
    // owns no drawing at all, so the guest's uploads must survive.
    .preserveVramBackdrop = 1,

    // --- memory card ------------------------------------------------------ this port's own key/path --
    .cardEnvVar = "PSXPORT_VAGRANT_CARD",
    .cardDefaultPath = "scratch/saves/vagrant.mcr",

    // --- frame pacing ------------------------------------------------ 1 field per pacing call, and why --
    // The framework REQUIRES this field ("a new game MUST set this field"): zero used to fall through
    // to reading the first consumer's engine byte out of the scratchpad, which in any other game is
    // ordinary working memory, so a second consumer slept on garbage. The semantics are by CALLING
    // CADENCE, not by the game's display rate — a port that still runs the guest's own frame loop and
    // paces once per FIELD sets 1, which is this port's shape (there is no native loop here). Revisit
    // together with RE-05 if a native loop ever calls the pacer once per logic frame.
    .paceQuota = 1,

    .windowTitle = "Vagrant Story (psxport)",
};

const GameConfig* vagrant_game_config() { return &g_vagrant_cfg; }

// Installs BOTH halves of the seam, because a Core's ctor snapshots them together — installing a
// config without its hooks leaves a Core holding a half-seam.
void vagrant_install_game_config() {
  extern const GameHooks* vagrant_game_hooks();   // game/core/game_hooks.cpp
  psxport_install_game(&g_vagrant_cfg, vagrant_game_hooks());
}
