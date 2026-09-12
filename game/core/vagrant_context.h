#pragma once

#include "cd/libds_field.h"
#include "core/overlay_images.h"
#include "core/resident_phase.h"
#include "input/pad_delivery.h"
#include "render/battle_frame.h"
#include "render/title_menu.h"
#include "render/title_movie.h"
#include "render/title_splash.h"
#include "render/title_startup.h"
#include "save/title_memcard_init.h"
#include "save/title_save_check.h"

#include <utility>

namespace vagrant {

// Game-level aggregate of cohesive per-Core products. Renderer state remains owned by its producer;
// adding another subsystem composes another member rather than growing VagrantRuntime into a god class.
struct VagrantContext {
  explicit VagrantContext(Core &core) : overlayImages(core) {
  }
  VagrantContext(Core &core, std::array<OverlaySpec, 3> specs) : overlayImages(core, std::move(specs)) {
  }

  OverlayImages overlayImages;
  cd::LibDsField libDsField{};
  ResidentPhase residentPhase{};
  PadDelivery padDelivery{};
  BattleFrameProducer battleFrame{};
  TitleMenuProducer titleMenu{};
  TitleSplashPhase titleSplash{};
  TitleMemcardInit titleMemcardInit{};
  TitleSaveCheck titleSaveCheck{};
  TitleStartupProducer titleStartup{};
  TitleMovieProducer titleMovie{};
};

} // namespace vagrant
