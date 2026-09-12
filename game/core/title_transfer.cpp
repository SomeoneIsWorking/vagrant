#include "core/title_transfer.h"

#include "core/resident_facts.h"

namespace vagrant {

OverlayLoadResult readAndLoadTitle(Core &core, OverlayImages &overlays, cd::ReadSector readSector) {
  auto transfer = cd::readNativeSectors(core, resident::kTitlePrgLba, resident::kTitlePrgSize, readSector);
  if (!transfer) {
    return {std::nullopt, transfer.detail};
  }
  return overlays.loadTransfer(OverlayKind::Title, transfer.sectors);
}

} // namespace vagrant
