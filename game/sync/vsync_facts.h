#pragma once

#include <cstdint>

namespace vagrant::sync {

// RE-10: Sony libetc VSync is read from the SHA-bound resident executable.
// Shipping admits only this measured leaf into PlatformHle, where psxport binds its mandatory
// native-frame-loop fatal handler. The half-open window is intentionally one instruction wide: no
// other resident library function has been classified as a native hardware-service boundary here.
inline constexpr std::uint32_t kVSync = 0x8001F6C4u;
inline constexpr std::uint32_t kVSyncWindowEnd = kVSync + 4u;

// RE-10 also measures the libetc FIELD COUNTER this same body polls, and the measurement is a
// cross-check rather than a single read: the query path, the wait target and
// the completion path of `VSync` to resolve to ONE address, requires `startIntrVSync` to CLEAR it,
// and requires the resident VBlank handler to read, increment and write it. A counter address that
// satisfied only one of those would be a guess with a measurement's name on it.
//
// It is declared because psxport's `PlatformHle::vsync` REFUSES a negative query without it: retail
// `VSync` called with `a0 < 0` returns the current field count rather than waiting, and the host has
// to return a number from guest memory. The guest's first VSync in this title is such a query
// (`CD_cw 0x80021470` calls `VSync(-1)`), so without this declaration the product aborted at the
// first measured CD command rather than running. The refusal is correct and the gap is here.
inline constexpr std::uint32_t kVSyncQueryCounter = 0x80032114u;

} // namespace vagrant::sync
