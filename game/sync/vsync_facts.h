#pragma once

#include <cstdint>

namespace vagrant::sync {

// libetc VSync, the one resident leaf admitted into PlatformHle (a one-instruction window).
inline constexpr std::uint32_t kVSync = 0x8001F6C4u;
inline constexpr std::uint32_t kVSyncWindowEnd = kVSync + 4u;

// The libetc field counter VSync polls; startIntrVSync clears it and the resident VBlank handler increments it.
// PlatformHle::vsync refuses a negative query without it, and CD_cw 0x80021470 calls VSync(-1).
inline constexpr std::uint32_t kVSyncQueryCounter = 0x80032114u;

} // namespace vagrant::sync
