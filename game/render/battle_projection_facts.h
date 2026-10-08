#pragma once

#include <cstdint>
#include <string_view>

namespace vagrant::battle_projection {

// Resident SDK leaves through which the guest states its viewport. Resident addresses are unambiguous;
// BATTLE, TITLE and ENDING all load at 0x80068800.
inline constexpr std::uint32_t kSetDefDrawEnv = 0x8002B374u;
inline constexpr std::uint32_t kSetDefDispEnv = 0x8002B434u;
inline constexpr std::uint32_t kSetGeomOffset = 0x80041540u;
// Observed, never modified: widening H is not available (see kProjectionDistanceWord).
inline constexpr std::uint32_t kSetGeomScreen = 0x80041534u;

// The one publication call site in BATTLE.PRG; the arguments are (320, 240, 0x8005E248, 0, 0, 0).
inline constexpr std::uint32_t kBattlePublicationCallSite = 0x8008A288u;
// The only call in INITBTL.PRG, with the same argument setup.
inline constexpr std::uint32_t kInitBtlPublicationCallSite = 0x800FA69Cu;

// BATTLE.PRG is an overlay: its addresses are not boot-exe ones.
inline constexpr std::uint32_t kBattleLoadBase = 0x80068800u;
// func_800760CC, the projection publication. It centres at y = 128; the presenter states 112 every field and its runs
// come last, which is why the owner sits on the leaf.

// The 256 is the DISPENV `screen` rect, not a clip: SetDefDispEnv zeroes `screen` and the publication fills it with
// (0, 8, 256, 224). SetDefDrawEnv fills the DRAWENV clip from its arguments; +0x0C/+0x0E is the texture window.
inline constexpr std::uint32_t kBattleViewportPublication = 0x800760CCu;
// The overlay's vertical centre at a 320x240 call; the presenter states 112.
inline constexpr std::int32_t kBattlePublicationCentreY = 128;
// The `screen` rect the publication installs.
inline constexpr std::int32_t kPublicationScreenX = 0;
inline constexpr std::int32_t kPublicationScreenY = 8;
inline constexpr std::int32_t kPublicationScreenWidth = 256;
inline constexpr std::int32_t kPublicationScreenHeight = 224;
// Drawing-area clip: 640 x 224 as two 320-wide halves, all literals at the one call site. The halves are the two
// frame buffers (DISPENVs 0x8005E188 and 0x8005E19C), so the clip is already twice the presented width.
inline constexpr std::uint32_t kBattleDrawEnv = 0x8005E0D0u;
inline constexpr std::uint32_t kBattleDrawEnvStride = 0x5Cu;
inline constexpr std::int32_t kBattleClipLeftX = 0;
inline constexpr std::int32_t kBattleClipRightX = 320;
inline constexpr std::int32_t kBattleClipWidth = 320;
inline constexpr std::int32_t kBattleClipHeight = 224;
// func_8007629C, the sole BATTLE field presenter: it loads the literals 160 and 112 before `jal 0x80041540`.
inline constexpr std::uint32_t kBattleFieldPresenter = 0x8007629Cu;
inline constexpr std::int32_t kBattlePresenterCentreX = 160;
inline constexpr std::int32_t kBattlePresenterCentreY = 112;
// func_8008A3A0, the dynamic-OT submit that hands the field to the presenter.
inline constexpr std::uint32_t kBattleDynamicOtSubmit = 0x8008A3A0u;
// vs_battle_setProjectionDistance: stores kProjectionDistanceWord and calls SetGeomScreen.
inline constexpr std::uint32_t kBattleProjectionDistanceSetter = 0x8007CCF0u;
// vs_battle_setNearClip: stores kNearClipWord and forwards to kBattleNearClipConsumer.
inline constexpr std::uint32_t kBattleNearClipSetter = 0x8007CCCCu;
// func_80098160, the near-clip consumer; named in the module map but not decompiled.
inline constexpr std::uint32_t kBattleNearClipConsumer = 0x80098160u;

// The resident viewport rectangle at 0x8005DFD4, written only by the overlay publication, so it is zero BSS during the
// resident boot. Stores run x, y, w, h but the addresses are x, w, y, h: width is +2 and height is +6.
inline constexpr std::uint32_t kProjectionDistanceWord = 0x8005E248u;
inline constexpr std::uint32_t kNearClipWord = 0x8005E0C8u;
inline constexpr std::uint32_t kViewportRectWord = 0x8005DFD4u;
inline constexpr std::uint32_t kViewportWidthWord = kViewportRectWord + 2u;
inline constexpr std::uint32_t kViewportHeightWord = kViewportRectWord + 6u;

// Both env leaves store the caller's width at +4 and height at +6 of the struct the caller names, so a publication's
// horizontal extent is not a title constant.
inline constexpr std::uint32_t kResidentDispEnv = 0x8005E188u;
inline constexpr std::uint32_t kLeafEnvWidthOffset = 4u;
inline constexpr std::uint32_t kLeafEnvHeightOffset = 6u;

// GTE control registers: SetGeomOffset (0x80041540) moves CR24 and CR25, SetGeomScreen (0x80041534)
// moves CR26. The transfer direction is not stated; it needs the COP2 encoding, not a field extract.
inline constexpr std::uint32_t kGteControlOfx = 24u;
inline constexpr std::uint32_t kGteControlOfy = 25u;
inline constexpr std::uint32_t kGteControlH = 26u;

// BATTLE branches on the projection distance, so raising it flips gameplay decisions and scales the GTE fog. Thresholds
// on the same word: below 272 at 0x8007458C, above 272 at 0x80074750, and a zoom step of +64 clamped at 768.
inline constexpr std::int32_t kProjectionDistanceBranchThreshold = 272;
inline constexpr std::int32_t kProjectionDistanceZoomClamp = 768;
inline constexpr std::int32_t kProjectionDistanceZoomStep = 64;

// The centre and the clip (the 640 x 224 DRAWENV pair) are owned, but the guest states its DISPLAY RESOLUTION through
// SetDefDispEnv and PutDispEnv turns that into the GPU mode word at 0x80028E80.
inline constexpr const char *kUnappliedBoundary =
    "the centre is owned and the clip is owned, but the guest states its DISPLAY RESOLUTION through "
    "SetDefDispEnv and a widening has to move that and the VRAM layout behind it; that is "
    "presentation infrastructure this port has not measured, so derive() is shipped and no widening "
    "is published";

// Constant-to-symbol pairs checked against the decompilation's module map; addresses absent here are not gated.
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

// Whether this title may widen yet.
inline constexpr std::string_view wideningBlocker() {
  return kUnappliedBoundary;
}

inline constexpr bool wideningAvailable() {
  return wideningBlocker().empty();
}

} // namespace vagrant::battle_projection
