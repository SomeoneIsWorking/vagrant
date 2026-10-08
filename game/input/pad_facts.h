#pragma once

#include <cstdint>

namespace vagrant::pad {

// Read from SLUS_010.40's unique _sysInit -> PadInitDirect call and its two driver-record stores.
inline constexpr std::uint32_t kSlot0Buffer = 0x8005DFF0u;
inline constexpr std::uint32_t kSlot1Buffer = 0x8005E012u;
inline constexpr std::uint32_t kDriverPointerTable = 0x8003FCF0u;
inline constexpr std::uint32_t kDriverPointerStride = 240u;

static_assert(kSlot1Buffer - kSlot0Buffer == 34u);

} // namespace vagrant::pad
