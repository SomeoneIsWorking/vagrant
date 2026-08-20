#ifndef VAGRANT_GAME_CD_DS_CONTROL_CONTRACT_H
#define VAGRANT_GAME_CD_DS_CONTROL_CONTRACT_H

#include <cstdint>

namespace vagrant_cd {

constexpr bool ownedControl(uint32_t command) {
  // Blocking commands whose effects and completion are represented by psxport's
  // synchronous controller. Query/result commands, sector reads, and XA remain
  // guest-owned.
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

} // namespace vagrant_cd

#endif // VAGRANT_GAME_CD_DS_CONTROL_CONTRACT_H
