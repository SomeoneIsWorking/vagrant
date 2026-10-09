#pragma once

#include "cd/native_file.h"
#include "images/overlay_images.h"

class Core;

namespace vagrant {

// `_loadBattlePrg`: both overlay files are read whole, then published; BATTLE replaces TITLE in slot 0.
OverlayLoadResult readAndLoadBattle(Core &core, OverlayImages &overlays, cd::ReadSector readSector);

} // namespace vagrant
