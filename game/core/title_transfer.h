#pragma once

#include "cd/native_file.h"
#include "core/overlay_images.h"

class Core;

namespace vagrant {

// Acquire the resident's complete sector extent, then authenticate before writing executable RAM.
OverlayLoadResult readAndLoadTitle(Core &core, OverlayImages &overlays, cd::ReadSector readSector);

} // namespace vagrant
