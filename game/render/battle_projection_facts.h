#pragma once

#include <cstdint>
#include <string_view>

namespace vagrant::battle_projection {

// Vagrant Story's guest projection publication, and the boundary that stops a widening today.
//
// PROVENANCE, AND IT IS TWO INDEPENDENT SOURCES. Every address below is named the same way by
// (a) this repository's own byte measurement, `tools/re_frame.py` running against the authenticated
// SLUS_010.40 executable, and (b) the vendored CC0 `external/rood-reverse` per-module symbol map
// (`config/SLUS_010.40/symbol_addrs.txt`, `config/BATTLE/BATTLE.PRG/symbol_addrs.txt`). All eight
// resident addresses were compared and all eight agree; `tools/re_projection.py` re-derives that
// comparison and fails when one stops agreeing. Neither source is the compiled game read at runtime,
// so the BODIES below remain a reconstruction — which is why the owner refuses instead of widening.

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

// The BATTLE.PRG sites, named in `config/BATTLE/BATTLE.PRG/exports.txt` and
// `symbol_addrs.txt`. BATTLE.PRG loads at 0x80068800, so these are OVERLAY addresses, not boot-exe
// ones: 933,925 bytes of this title's code live in .PRG overlays and the projection is one of them.
inline constexpr std::uint32_t kBattleLoadBase = 0x80068800u;
// func_800760CC — THE projection publication owner. Called as (320, 240, projectionDistance, 0,0,0)
// from BATTLE.PRG 0x8008B0A4 and INITBTL.PRG; it writes OFX/OFY through SetGeomOffset, H through
// SetGeomScreen, both draw areas, both display areas, both screen rectangles, and the resident
// viewport rectangle. `docs/battle-rendering.md` records this as the viewport initializer 0x800760CC
// measured from BATTLE.PRG bytes; the decomp names the same address func_800760CC.
inline constexpr std::uint32_t kBattleViewportPublication = 0x800760CCu;
// func_8007629C — the sole BATTLE field presenter, and the per-field re-publication of a literal
// horizontal centre. Recorded in `docs/battle-rendering.md` as measured from bytes.
inline constexpr std::uint32_t kBattleFieldPresenter = 0x8007629Cu;
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

// Resident BSS words. Both are in the RESIDENT module (`config/SLUS_010.40/symbol_addrs.txt`), not in
// an overlay, so both stay valid across a BATTLE load. kViewportRectWord is the first of four
// adjacent shorts written as a rectangle in the order x, y, w, h.
inline constexpr std::uint32_t kProjectionDistanceWord = 0x8005E248u;
inline constexpr std::uint32_t kNearClipWord = 0x8005E0C8u;
inline constexpr std::uint32_t kViewportRectWord = 0x8005DFD4u;
// The width half of that rectangle, published by the same call that publishes the height.
inline constexpr std::uint32_t kViewportWidthWord = kViewportRectWord + 2u;
inline constexpr std::uint32_t kViewportHeightWord = kViewportRectWord + 6u;

// The GTE control-register numbers, named once so the meaning lives with the number.
inline constexpr std::uint32_t kGteControlOfx = 24u;
inline constexpr std::uint32_t kGteControlOfy = 25u;
inline constexpr std::uint32_t kGteControlH = 26u;

// WHY THE PROJECTION DISTANCE IS NEVER WIDENED, AS A CONSTANT BECAUSE IT IS A THRESHOLD.
// `vs_main_projectionDistance` is not only a projection parameter: two BATTLE functions BRANCH on it
// against this value. tools/re_projection.py cites the decompiled sites. A widening that raised the
// word past it would flip a gameplay decision, and the value also scales the GTE fog
// (`SetFogNear(768, vs_main_projectionDistance)`). Widening the canvas instead leaves the word at
// the retail value and avoids both.
inline constexpr std::int32_t kProjectionDistanceBranchThreshold = 272;

// The single named boundary that stops this title widening today. The horizontal CENTRE is
// derivable at a resident leaf, because the leaf's argument is the title's own value on every call.
// The horizontal CLIP is not: the guest publishes its draw and display areas from the overlay
// publication with a side-by-side VRAM layout and a screen rectangle that the reconstruction reports
// as 256 against a 320-wide display area, in two independently written modules. Re-deriving that
// needs the bytes, so a centre-only move would CROP the left of every field rather than widen it,
// and the owner refuses instead.
inline constexpr const char *kUnappliedBoundary =
    "the horizontal clip is published by the overlay from a VRAM layout and a screen rectangle this "
    "port has not read from bytes; moving the centre alone would crop the left of every field";

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
