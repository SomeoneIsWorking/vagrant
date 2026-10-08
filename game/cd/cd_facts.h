#pragma once

#include <cstdint>

namespace vagrant::cd {

// libcd/libds leaves. CD_cw contains two waits and CD_init calls CD_sync directly; both are bound so no guest VSync
// query is reachable.
inline constexpr std::uint32_t kDsControlB = 0x80025BE4u;
inline constexpr std::uint32_t kCdCommand = 0x80021470u;
inline constexpr std::uint32_t kCdCommandWindowEnd = kCdCommand + 4u;
inline constexpr std::uint32_t kCdSync = 0x80020F28u;
inline constexpr std::uint32_t kCdSyncWindowEnd = kCdSync + 4u;

// _diskReset leaf and state addresses.
inline constexpr std::uint32_t kDsFlush = 0x800243A0u;
inline constexpr std::uint32_t kDiskState = 0x80055D10u;
inline constexpr std::uint32_t kDsControlBuffer = 0x80055D2Cu;
inline constexpr std::uint32_t kCdReadBuffer = 0x80050110u;

// The libds system-state word and its Busy/Ready values.
inline constexpr std::uint32_t kSystemState = 0x8003269Cu;
inline constexpr std::uint32_t kCommandDeadline = 0x800326C0u;
inline constexpr std::uint32_t kSystemReady = 1u;
inline constexpr std::uint32_t kSystemBusy = 2u;
inline constexpr std::uint32_t kFieldStatusTick = 0x80024BDCu;

// Blocking libds CONTROL commands psxport's synchronous CD controller can complete; others are refused.
constexpr bool ownedControl(std::uint32_t command) {
  switch (command) {
  case 0x01: // Nop
  case 0x02: // Setloc
  case 0x07: // Standby
  case 0x08: // Stop
  case 0x09: // Pause
  case 0x0D: // Setfilter
  case 0x0E: // Setmode
  case 0x15: // SeekL
  case 0x16: // SeekP
    return true;
  default:
    return false;
  }
}

} // namespace vagrant::cd
