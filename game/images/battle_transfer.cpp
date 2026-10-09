#include "images/battle_transfer.h"

#include "boot/resident_facts.h"

namespace vagrant {

OverlayLoadResult readAndLoadBattle(Core &core, OverlayImages &overlays, cd::ReadSector readSector) {
  auto battle = cd::readNativeSectors(core, resident::kBattlePrgLba, resident::kBattlePrgSize, readSector);
  if (!battle) {
    return {std::nullopt, battle.detail};
  }
  auto initBattle = cd::readNativeSectors(core, resident::kInitBtlPrgLba, resident::kInitBtlPrgSize, readSector);
  if (!initBattle) {
    return {std::nullopt, initBattle.detail};
  }
  OverlayLoadResult loadedBattle = overlays.loadTransfer(OverlayKind::Battle, battle.sectors);
  if (!loadedBattle) {
    return loadedBattle;
  }
  return overlays.loadTransfer(OverlayKind::InitBattle, initBattle.sectors);
}

} // namespace vagrant
