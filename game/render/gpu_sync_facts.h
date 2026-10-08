#pragma once

#include <cstdint>

namespace vagrant::gpu {

// PsyQ libgpu GPU-command timeout leaf, called by queue owner 0x8002A3E8 from ClearImage 0x800287D4. It reads
// VSync(-1) and stores +240 in kTimeoutDeadline, so it is a platform service and no guest VSync runs.
inline constexpr std::uint32_t kTimeoutArm = 0x8002AB84u;
inline constexpr std::uint32_t kTimeoutArmWindowEnd = kTimeoutArm + 4u;
inline constexpr std::uint32_t kTimeoutDeadline = 0x80033580u;
inline constexpr std::uint32_t kTimeoutFlag = 0x80033584u;

} // namespace vagrant::gpu