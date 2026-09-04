#pragma once

#include <cstdint>

namespace vagrant::gpu {

// RE-21: the bounded product trace and tools/re_resident.py identify this as PsyQ libgpu's
// GPU-command timeout arm. ClearImage 0x800287D4 reaches queue owner 0x8002A3E8, which calls this
// leaf before submitting the command. Its retail body reads VSync(-1), stores that value + 240 in
// kTimeoutDeadline, and clears kTimeoutFlag. The host GPU completes the command synchronously, so
// psxport owns this exact leaf without dispatching the guest VSync query.
inline constexpr std::uint32_t kTimeoutArm = 0x8002AB84u;
inline constexpr std::uint32_t kTimeoutArmWindowEnd = kTimeoutArm + 4u;
inline constexpr std::uint32_t kTimeoutDeadline = 0x80033580u;
inline constexpr std::uint32_t kTimeoutFlag = 0x80033584u;

} // namespace vagrant::gpu
