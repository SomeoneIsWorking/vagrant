#pragma once

#include <cstdint>

namespace vagrant::sync {

// RE-10: tools/re_vblank.py derives Sony libetc VSync from the SHA-bound resident executable.
// Shipping admits only this measured leaf into PlatformHle, where psxport binds its mandatory
// native-frame-loop fatal handler. The half-open window is intentionally one instruction wide: no
// other resident library function has been classified as a native hardware-service boundary here.
inline constexpr std::uint32_t kVSync = 0x8001F6C4u;
inline constexpr std::uint32_t kVSyncWindowEnd = kVSync + 4u;

} // namespace vagrant::sync
