#pragma once

#include <cstdint>
#include <string_view>

namespace vagrant::battle_projection {

// Vagrant Story's guest projection publication, and the boundary that stops a widening today.
//
// PROVENANCE, AND IT IS THREE INDEPENDENT SOURCES NOW. Every address below is named the same way by
// (a) this repository's own byte measurement, `tools/re_frame.py` running against the authenticated
// SLUS_010.40 executable, (b) the vendored CC0 `external/rood-reverse` per-module symbol map
// (`config/SLUS_010.40/symbol_addrs.txt`, `config/BATTLE/BATTLE.PRG/symbol_addrs.txt`), and (c) since
// 2026-09-27 `tools/re_viewport.py`, which reads the INSTRUCTION WORDS at each address out of the
// SHA-bound image itself.
//
// (c) IS NOT A THIRD VOTE, IT IS A DIFFERENT KIND OF STATEMENT, and the difference is why the
// conclusions below changed. (a) and (b) agree on WHICH function lives at an address. Neither can say
// what the function DOES, and issue 0037 recorded the consequence: the owner shipped no widening
// because not one instruction word of the four leaves had been read, and the decompilation's bodies
// were "unverified". `re_viewport.py` has now read them, and 24 of its 26 claims are CONFIRMED with
// the settling words printed, 1 is REFUTED (the BATTLE call site is 0x8008A288, NOT the 0x8008B0A4
// this file previously stated) and 1 is NOT DETERMINABLE. So the bodies are no longer a
// reconstruction and the reasons below are no longer a reconstruction's — which is the whole point,
// and it is why the two REFUTED/UNDETERMINED entries are named here rather than dropped.

// The four RESIDENT SDK leaves through which the guest states its viewport. They are resident, not
// overlay, so one address is one address: BATTLE, TITLE and ENDING all reuse load base 0x80068800
// and none of them can collide here. Owning the leaves rather than the overlay's call site is what
// makes the horizontal centre re-latch every field: BATTLE's presenter re-states a literal centre
// through SetGeomOffset on every field, and it goes through this leaf like every other caller.
inline constexpr std::uint32_t kSetDefDrawEnv = 0x8002B374u;
inline constexpr std::uint32_t kSetDefDispEnv = 0x8002B434u;
inline constexpr std::uint32_t kSetGeomOffset = 0x80041540u;
// Observed and NEVER modified. See kProjectionDistanceWord for why widening H is not available.
inline constexpr std::uint32_t kSetGeomScreen = 0x80041534u;

// The ONE call site of the publication inside BATTLE.PRG, read from the bytes.
//
// CORRECTED 2026-09-27. This file previously said the call was at 0x8008B0A4. That address holds
// `and $t2, $t1, $t5` — a 16-bit mask inside a CLUT-addressing loop, not a call of anything.
// `re_viewport.py` census over BATTLE.PRG's declared code extent finds EXACTLY ONE `jal` of this
// function, at 0x8008A288, preceded by the argument setup it asserts:
//
//     0x8008A270  addiu $a0, $zero, 0x140        ; 320
//     0x8008A274  addiu $a1, $zero, 0xF0         ; 240
//     0x8008A278  lui  $v0, 0x8006
//     0x8008A27C  lw   $a2, -0x1DB8($v0)         ; 0x8005E248
//     0x8008A280  addu $a3, $zero, $zero         ; 0
//     0x8008A284  sw   $zero, 0x10($sp)          ; fifth argument
//     0x8008A288  jal  0x800760CC
//     0x8008A28C  sw   $zero, 0x14($sp)          ; sixth argument
//
// A wrong address here is not cosmetic: it is the address the owner would have attributed a
// viewport publication to, and the previous value pointed at a word that computes a mask.
inline constexpr std::uint32_t kBattlePublicationCallSite = 0x8008A288u;
// And the only one in INITBTL.PRG, at 0x800FA69C, with the identical argument setup.
inline constexpr std::uint32_t kInitBtlPublicationCallSite = 0x800FA69Cu;

// The BATTLE.PRG sites, named in `config/BATTLE/BATTLE.PRG/exports.txt` and
// `symbol_addrs.txt`. BATTLE.PRG loads at 0x80068800, so these are OVERLAY addresses, not boot-exe
// ones: 933,925 bytes of this title's code live in .PRG overlays and the projection is one of them.
inline constexpr std::uint32_t kBattleLoadBase = 0x80068800u;
// func_800760CC — THE projection publication owner, and the body IS NOW READ FROM BYTES.
//
// Called as (320, 240, vs_main_projectionDistance, 0, 0, 0) from BATTLE.PRG 0x8008A288 and
// INITBTL.PRG 0x800FA69C, and `re_viewport.py` CONFIRMS both call sites and both argument setups
// from the words. What the body does, each line read from BATTLE.PRG at file offset 0xD8CC:
//
//     0x800760D4  move $s2, $a0                 ; width
//     0x800760D8  srl  $a0, $s2, 31             ; + the signed-halving idiom below gives width/2
//     0x800760DC  addu $a0, $s2, $a0
//     0x800760E0  sra  $a0, $a0, 1              ; OFX = width / 2
//     0x800760E8  addiu $s3, $a1, -0x10         ; height - 16: the 16-line convention, CONFIRMED
//     0x80076108  addiu $a1, $a1, 0x10          ; OFY = (height-16)/2 + 16  ==  128 at 320x240
//     0x80076124  jal  0x80041540               ; SetGeomOffset
//     0x8007612C  jal  0x80041534               ; SetGeomScreen(H = arg2)
//     0x8007614C / 0x80076188  jal 0x8002B374   ; SetDefDrawEnv, TWICE
//     0x8007616C / 0x800761A0  jal 0x8002B434   ; SetDefDispEnv, TWICE
//     0x800761B8..0x800761D8                    ; both `screen` rects := (0, 8, 256, 224)
//     0x800761E0..0x80076200                    ; the resident rect at 0x8005DFD4
//
// TWO FACTS HERE THAT NOBODY HAD BEFORE, and both are load-bearing for the widening question.
//
// 1. THE OVERLAY'S VERTICAL CENTRE IS 128, NOT 112. The decompilation elided it as
//    `SetGeomOffset(arg0 / 2, …)` and the presenter's literal (160, 112) is what filled the gap. The
//    bytes show the two sites genuinely DISAGREE: the publication states (160, 128) and the presenter
//    re-states (160, 112) every field. The presenter's is the one that governs the field, because it
//    runs last — which is precisely why the owner sits on the leaf.
//
// 2. THE 256 IS A LITERAL IN A `screen` RECT, AND IT IS NOT A CLIP. This is the correction the
//    previous arm's blocker rested on, and it is the most consequential result of reading the bytes.
//    `SetDefDispEnv` at 0x8002B434 writes its four arguments to DISPENV +0/+2/+4/+6 and ZEROES
//    +8/+0xA/+0xC/+0xE, so +0..+6 is the `disp` rect and +8..+0xE is the `screen` rect. The
//    publication calls `SetDefDispEnv(disp, 320, 0, 320, 224)` and then OVERWRITES the `screen` rect
//    with the LITERALS x=0, y=8, w=256, h=224. Meanwhile `SetDefDrawEnv` at 0x8002B374 writes the
//    DRAW-AREA clip (DRAWENV +0xC/+0xE) as ZERO and the publication never stores there.
//
//    So there is NO 256-pixel horizontal clip in this title's draw path. The 256 is the display
//    window's width, in the same struct the 320 lives in, and the drawing area is UNCLIPPED. A
//    widening is therefore not blocked by a 256-pixel clip this port could not interpret.
//
//    BUT IT IS STILL NOT OWNED, and the reason is a different and stronger one, stated in
//    kUnappliedBoundary below. The honest correction is to the REASON, not to the outcome.
inline constexpr std::uint32_t kBattleViewportPublication = 0x800760CCu;
// The overlay's own vertical centre at a 320x240 call, which the bytes show is 128 and not the 112
// the presenter states. Recorded because "the two sites disagree" is only checkable if both numbers
// are named, and the previous file asserted the disagreement while stating only one of them.
inline constexpr std::int32_t kBattlePublicationCentreY = 128;
// The `screen` rect the publication installs, as literals rather than as derived values.
inline constexpr std::int32_t kPublicationScreenX = 0;
inline constexpr std::int32_t kPublicationScreenY = 8;
inline constexpr std::int32_t kPublicationScreenWidth = 256;
inline constexpr std::int32_t kPublicationScreenHeight = 224;
// func_8007629C — the sole BATTLE field presenter, and the per-field re-publication of a literal
// horizontal centre. CONFIRMED from BATTLE.PRG bytes: at 0x800762E0/0x800762E4 it holds
// `addiu $a0, $zero, 0xA0` (160) and `addiu $a1, $zero, 0x70` (112) immediately before
// `jal 0x80041540`. Those are LITERALS in the instruction stream, not values loaded from anywhere,
// which is the whole reason an owner on the overlay's call site would be overwritten once per field.
// The presenter also re-issues PutDispEnv/PutDrawEnv every field (0x80076400, 0x8007642C), so the
// publication's `screen` rect is PER-FIELD state rather than a one-shot.
inline constexpr std::uint32_t kBattleFieldPresenter = 0x8007629Cu;
inline constexpr std::int32_t kBattlePresenterCentreX = 160;
inline constexpr std::int32_t kBattlePresenterCentreY = 112;
// func_8008A3A0 — the dynamic-OT submit that hands the field to the presenter.
inline constexpr std::uint32_t kBattleDynamicOtSubmit = 0x8008A3A0u;
// vs_battle_setProjectionDistance — stores its argument to kProjectionDistanceWord and calls
// SetGeomScreen. `config/BATTLE/BATTLE.PRG/symbol_addrs.txt` line 74 names it 0x8007CCF0, matching
// the setter `docs/battle-rendering.md` measured at 0x8007CCF0.
inline constexpr std::uint32_t kBattleProjectionDistanceSetter = 0x8007CCF0u;
// vs_battle_setNearClip — stores kNearClipWord and forwards to kBattleNearClipConsumer.
inline constexpr std::uint32_t kBattleNearClipSetter = 0x8007CCCCu;
// func_80098160 — the near-clip consumer. NAMED IN THE MODULE MAP AND NOT DECOMPILED: the symbol
// exists, no body does. So this title's near plane is known to exist and is not known to be read by
// anything, and the owner must not claim otherwise.
inline constexpr std::uint32_t kBattleNearClipConsumer = 0x80098160u;

// The RESIDENT viewport rectangle. BOTH halves of this statement were measured on 2026-09-28 and the
// second is the one the first run got wrong.
//
// 0x8005DFD4..0x8005DFDA are four adjacent shorts written as a rectangle. BATTLE.PRG's publication
// writes them, in the order x (0x8005DFD4), y (0x8005DFD8), w (0x8005DFD6), h (0x8005DFDA) — so the
// STORE order is x, y, w, h while the ADDRESSES are x, w, y, h, and kViewportWidthWord and
// kViewportHeightWord are +2 and +6 and NOT +4 and +6. A reader who assumed the store order equalled
// the memory order would put the width 2 bytes off.
//
// THESE ARE THE OVERLAY PUBLICATION'S RECTANGLE AND NOT THE BOOT'S, and `tools/re_viewport.py`
// decides that from a reference census over all four provisioned modules: the resident executable
// names NONE of the four halfwords, and the only stores anywhere are the overlay publication's own
// four at 0x800761E0/0x800761E8/0x800761F0/0x80076200. So the word is still zero BSS while the
// resident boot runs, and an owner that cross-checks a RESIDENT display-area publication against it
// compares a live 320 against a word nothing has written. That is exactly the disagreement the first
// run aborted on, and it is why these constants are BATTLE/ENDING state rather than a second
// statement of whatever the boot just published.
inline constexpr std::uint32_t kProjectionDistanceWord = 0x8005E248u;
inline constexpr std::uint32_t kNearClipWord = 0x8005E0C8u;
inline constexpr std::uint32_t kViewportRectWord = 0x8005DFD4u;
// The width half of that rectangle, published by the same call that publishes the height.
inline constexpr std::uint32_t kViewportWidthWord = kViewportRectWord + 2u;
inline constexpr std::uint32_t kViewportHeightWord = kViewportRectWord + 6u;

// THE WORD THAT IS A DISPLAY-AREA PUBLICATION'S OWN HORIZONTAL EXTENT, and it is not a constant.
//
// Both env leaves store the width the CALLER stated into the struct that caller named, at +4 of it,
// and the height at +6. Read from the leaves' own words, by `re_viewport.py`:
//
//     0x8002B434  SetDefDispEnv  addu $v0, $a0, $zero ; lw  $v1, 16($sp)   ; the fifth argument
//     0x8002B43C                 sh   $a1, 0($v0)     ; +0 x
//     0x8002B440                 sh   $a2, 2($v0)     ; +2 y
//     0x8002B444                 sh   $a3, 4($v0)     ; +4 w   <- the stated width
//     0x8002B46C  (delay slot)   sh   $v1, 6($v0)     ; +6 h
//
//     0x8002B374  SetDefDrawEnv  addu $s1, $a0, $zero ; lw  $s2, 56($sp)  ; the fifth argument
//     0x8002B3A4  (delay slot)   addu $s0, $a3, $zero
//     0x8002B3B4                 sh   $s0, 4($s1)     ; +4 w   <- the stated width
//     0x8002B3DC  (delay slot)   sh   $s2, 6($s1)     ; +6 h
//
// So the cross-check the owner owes is between the register the guest stated and the word the LEAF
// stored it in, and the second of those is at `env + 4` for a per-call `env` the caller names. A
// publication's own horizontal extent is therefore NOT a title constant, and writing one down as if
// it were is what produced the abort.
//
// THE RESIDENT'S DISPLAY ENVIRONMENT, so the boot's per-call value is a number rather than a
// derivation: `vs_main_dispEnv` is named 0x8005E188 by the decompilation's own
// `config/SLUS_010.40/symbol_addrs.txt` (line 790) and is built in the resident body at 0x80042060
// as `lui $s0, 0x8006` + `addiu $s0, $s0, -7800`, so the boot's width word is 0x8005E18C and its
// height word 0x8005E18A. Those two are recorded for the boot's OWN publication, which `re_viewport`
// confirms is `_initScreen` at 0x80042054 handing the leaf a width of 320 from its own `$a0`; they
// are documentation of one caller, not the cross-check target, because the overlays publish through
// their own copies of the same globals.
inline constexpr std::uint32_t kResidentDispEnv = 0x8005E188u;
inline constexpr std::uint32_t kLeafEnvWidthOffset = 4u;
inline constexpr std::uint32_t kLeafEnvHeightOffset = 6u;

// The GTE control-register numbers, named once so the meaning lives with the number.
//
// CONFIRMED FROM THE LEAVES' OWN WORDS, which is the check that matters because the owner compares
// the framework's record against these registers on every call. `SetGeomOffset` is three words and
// names CR24 and CR25; `SetGeomScreen` is one and names CR26:
//
//     0x80041540  sll  $a0, $a0, 16
//     0x80041544  sll  $a1, $a1, 16
//     0x80041548  cop2 register move, CR24
//     0x8004154C  cop2 register move, CR25
//     0x80041550  jr $ra
//     0x80041534  cop2 register move, CR26
//     0x80041538  jr $ra
//
// This is what psxport's `proj_params.h` already documents for libgte ("CR24 = ofx << 16;
// CR25 = ofy << 16 and CR26 = h"), so the two independent sources agree — and the agreement is now
// on the INSTRUCTIONS rather than on a reconstruction of them.
//
// THE TRANSFER DIRECTION IS DELIBERATELY NOT STATED HERE, and that is a correction rather than an
// omission. `tools/re_viewport.py` used to name every one of these `mtc2` or `mfc2` from bit 25
// alone, so it labelled a WRITE as a READ on every GTE register move it printed, and the previous
// revision of this header hedged the same hedge (`mtc2/mfc2`) because the tool's label was not
// trustworthy. Naming a direction needs the R3000A COP2 transfer encoding, which is a reference and
// not a field extraction; the tool now reports the register number and the raw selector and names no
// direction, which is what a field extractor can actually establish.
inline constexpr std::uint32_t kGteControlOfx = 24u;
inline constexpr std::uint32_t kGteControlOfy = 25u;
inline constexpr std::uint32_t kGteControlH = 26u;

// WHY THE PROJECTION DISTANCE IS NEVER WIDENED, AS A CONSTANT BECAUSE IT IS A THRESHOLD.
// `vs_main_projectionDistance` is not only a projection parameter: BATTLE functions BRANCH on it
// against this value. tools/re_projection.py cites the decompiled sites; `re_viewport.py` settles the
// two branches from the BYTES, at 0x80074580 and 0x80074744, and finds a THIRD threshold the
// decompilation had not recorded. A widening that raised the word past any of them would flip a
// gameplay decision, and the value also scales the GTE fog. Widening the canvas instead leaves the
// word alone and avoids all of them.
//
// THE THREE THRESHOLDS, all measured, all on the same word, and all of them gameplay:
//
//   0x8007458C  slti $v0, $v0, 0x110     ; < 272  — func_80074580, from decomp 146C.c:4209
//   0x80074750  slti $v0, $v0, 0x111     ; > 272, spelled `< 273` — func_80074744, decomp 146C.c:4266
//   0x8007858C  slti $v0, $v0, 0x300     ; a zoom step: the word grows by 64 and clamps at 768
//
// 768 is the one that is NEW here, and it is the one that would bite a widening which "just nudged
// H". The word is not a free parameter with a comfortable headroom: the game drives it across
// [0x100, 0x300] and branches at three points inside that range.
inline constexpr std::int32_t kProjectionDistanceBranchThreshold = 272;
inline constexpr std::int32_t kProjectionDistanceZoomClamp = 768;
inline constexpr std::int32_t kProjectionDistanceZoomStep = 64;

// The single named boundary that stops this title widening today.
//
// REWRITTEN 2026-09-27, AND THE REASON CHANGED. The previous text said the horizontal CLIP "is
// published by the overlay from a VRAM layout and a screen rectangle this port has not read from
// bytes". The bytes have now been read, and they REFUTE that reason: `re_viewport.py` CONFIRMS that
// the 256 is a literal in the DISPENV `screen` rect and CONFIRMS that `SetDefDrawEnv` writes the
// DRAW-AREA clip to zero and the publication never touches it. There is no 256-pixel clip in this
// title's draw path to move. Keeping the old sentence would have left a REFUTED claim standing as
// the port's reason, which is worse than having had no reason: a reader checking the clip would
// conclude the boundary was a measurement when it was a guess about a measurement.
//
// THE REAL BOUNDARY, WHICH IS STRONGER. A widening is the PAIR (centre, clip) and BOTH halves are
// per-field, so the two halves have to move in the same field or one of them is a translation:
//
//   * the CENTRE is re-stated every field as a LITERAL (160, 112) by the presenter, so it is only
//     interceptable at the resident `SetGeomOffset` leaf — which is where this owner already sits;
//   * the CLIP is the `screen` rect, and `SetDefDispEnv` ZEROES it, so the publication's literals are
//     the only clip in the field, written by the overlay ONCE at area entry and then re-Put every
//     field by the presenter.
//
// So both halves are owned, and the derivation would have a complete publication to work from. What
// is NOT owned is the thing a widening would actually change: `SetDefDispEnv(disp, 320, 0, 320, 224)`
// selects the DISPLAY RESOLUTION, and `PutDispEnv` at 0x80028E80 turns that rect into the GPU's
// display-mode word. Widening therefore means moving the guest's display mode and its VRAM layout,
// and that is presentation infrastructure this port has not measured and cannot verify without a
// running adapter (S015). `derive()` is shipped and correct; the widening is not published because
// the other end of the pair has nowhere to land yet.
inline constexpr const char *kUnappliedBoundary =
    "the centre is owned and the clip is owned, but the guest states its DISPLAY RESOLUTION through "
    "SetDefDispEnv and a widening has to move that and the VRAM layout behind it; that is "
    "presentation infrastructure this port has not measured, so derive() is shipped and no widening "
    "is published";

// THE DECOMPILATION'S OWN NAME FOR EACH ADDRESS, declared here and gated by tools/re_projection.py.
//
// This table exists because the obvious gate — "does the shipping constant's name equal the name at
// that address?" — is red for a reason that has nothing to do with the address: the module map says
// `vs_main_projectionDistance` where this header says `kProjectionDistanceWord`, and a gate that is
// permanently red for a naming convention trains its reader to ignore it. So the correspondence is
// STATED, and the gate checks the claim that can actually be wrong: does that address hold that
// symbol? A declared pair the module map does not corroborate fails the census.
//
// An address absent from this table is not gated, and is reported as undeclared with a count. That
// is the honest scope: the decompilation gives no address for `func_800760CC` (it appears in
// config/BATTLE/BATTLE.PRG/exports.txt, which carries names and no addresses), so the module map
// cannot corroborate it and pretending otherwise would be the guess this gate exists to prevent.
struct DecompSymbol {
  const char *constant; // the shipping constant
  const char *symbol;   // the name config/*/symbol_addrs.txt uses at that address
};

inline constexpr DecompSymbol kDecompSymbols[] = {
    {"kSetDefDrawEnv", "SetDefDrawEnv"},
    {"kSetDefDispEnv", "SetDefDispEnv"},
    {"kSetGeomOffset", "SetGeomOffset"},
    {"kSetGeomScreen", "SetGeomScreen"},
    {"kBattleProjectionDistanceSetter", "vs_battle_setProjectionDistance"},
    {"kBattleNearClipSetter", "vs_battle_setNearClip"},
    {"kBattleNearClipConsumer", "func_80098160"},
    {"kProjectionDistanceWord", "vs_main_projectionDistance"},
    {"kNearClipWord", "vs_main_nearClip"},
};

// THE SINGLE SOURCE OF TRUTH for whether this title may widen yet. Both the per-Core owner and the
// framework's stateless aspect policy read these two, so "4:3 until the clip is owned" has one
// implementation rather than a comment in each place that can drift into disagreeing.
inline constexpr std::string_view wideningBlocker() {
  return kUnappliedBoundary;
}

inline constexpr bool wideningAvailable() {
  return wideningBlocker().empty();
}

} // namespace vagrant::battle_projection
