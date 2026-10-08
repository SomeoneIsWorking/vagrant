#pragma once

#include "cd/native_file.h"
#include "images/overlay_images.h"

class Core;

namespace vagrant {

// Acquires the resident's complete sector extent and authenticates it before writing executable RAM.
OverlayLoadResult readAndLoadTitle(Core &core, OverlayImages &overlays, cd::ReadSector readSector);

} // namespace vagrant
