#pragma once

#include <cstdint>

namespace vagrant::title_splash {

// RE-12/RE-23: SHA-bound TITLE.PRG facts measured by tools/re_title_startup.py. The host phase
// retains the exact finite leaves around _displayPublisherAndDeveloper's VSync boundaries.
inline constexpr std::uint32_t kInitGameData = 0x80071B14u;
inline constexpr std::uint32_t kGameSaveScreen = 0x8006EDBCu;
inline constexpr std::uint32_t kMemset = 0x80026EB4u;
inline constexpr std::uint32_t kDrawImage = 0x80068BDCu;
inline constexpr std::uint32_t kDrawSprite = 0x8006A778u;
inline constexpr std::uint32_t kClearImage = 0x800287D4u;
inline constexpr std::uint32_t kSetDefDispEnv = 0x8002B434u;
inline constexpr std::uint32_t kSetDefDrawEnv = 0x8002B374u;
inline constexpr std::uint32_t kPutDispEnv = 0x80028E80u;
inline constexpr std::uint32_t kPutDrawEnv = 0x80028CB4u;
inline constexpr std::uint32_t kDrawSync = 0x80028650u;
inline constexpr std::uint32_t kSetDispMask = 0x800285B8u;
inline constexpr std::uint32_t kProcessPadState = 0x80043940u;
inline constexpr std::uint32_t kSetMonoSound = 0x800468BCu;
inline constexpr std::uint32_t kSetCdVolume = 0x80013230u;
inline constexpr std::uint32_t kCopyTitleBgData = 0x8006FC6Cu;

inline constexpr std::uint32_t kSettings = 0x80060020u;
inline constexpr std::uint32_t kTitleScreenCount = 0x8004A528u;
inline constexpr std::uint32_t kInventoryIndices = 0x800619D8u;
inline constexpr std::uint32_t kStateFlags = 0x80061598u;
inline constexpr std::uint32_t kIntroMoviePlaying = 0x800DED7Cu;
inline constexpr std::uint32_t kMenuItemStates = 0x800EFDF8u;
inline constexpr std::uint32_t kButtonsState = 0x8005E238u;
inline constexpr std::uint32_t kPublisherData = 0x80072F0Cu;
inline constexpr std::uint32_t kDeveloperData = 0x8007472Cu;

} // namespace vagrant::title_splash
