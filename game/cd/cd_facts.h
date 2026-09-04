#pragma once

#include <cstdint>

namespace vagrant::cd {

// RE-04 / RE-20: tools/re_cd.py derives these Sony libcd/libds leaves from the SHA-bound
// SLUS_010.40. DsControlB remains the title-owned synchronous command wrapper. CD_cw and CD_sync
// are independent platform-service leaves: CD_cw contains two waits, while CD_init also calls
// CD_sync directly. Binding both exact instructions keeps every guest VSync query unreachable.
inline constexpr std::uint32_t kDsControlB = 0x80025BE4u;
inline constexpr std::uint32_t kCdCommand = 0x80021470u;
inline constexpr std::uint32_t kCdCommandWindowEnd = kCdCommand + 4u;
inline constexpr std::uint32_t kCdSync = 0x80020F28u;
inline constexpr std::uint32_t kCdSyncWindowEnd = kCdSync + 4u;

// _diskReset finite leaf/state facts measured by tools/re_resident.py.
inline constexpr std::uint32_t kDsFlush = 0x800243A0u;
inline constexpr std::uint32_t kDiskState = 0x80055D10u;
inline constexpr std::uint32_t kDsControlBuffer = 0x80055D2Cu;
inline constexpr std::uint32_t kCdReadBuffer = 0x80050110u;

// RE-05 / RE-22: tools/re_async_cd.py derives the indexed libds system-state word, the Busy and
// Ready values consumed by DsSystemStatus, and the finite status transition formerly registered on
// the guest VBlank path. The host field owner invokes that transition directly; it never invokes
// guest VSync.
inline constexpr std::uint32_t kSystemState = 0x8003269Cu;
inline constexpr std::uint32_t kCommandDeadline = 0x800326C0u;
inline constexpr std::uint32_t kSystemReady = 1u;
inline constexpr std::uint32_t kSystemBusy = 2u;
inline constexpr std::uint32_t kFieldStatusTick = 0x80024BDCu;

} // namespace vagrant::cd
