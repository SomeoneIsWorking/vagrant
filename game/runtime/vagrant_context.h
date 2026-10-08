#pragma once

#include "boot/resident_phase.h"
#include "cd/libds_field.h"
#include "images/overlay_images.h"
#include "input/pad_delivery.h"
#include "render/battle_frame.h"
#include "render/battle_projection.h"
#include "render/title_menu.h"
#include "render/title_movie.h"
#include "render/title_splash.h"
#include "render/title_startup.h"
#include "save/title_memcard_init.h"
#include "save/title_save_check.h"

#include <utility>

namespace vagrant {

// Aggregate of per-Core title products.
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
  // Per-Core; the title re-authors its viewport every field, so nothing is remembered.
  BattleProjectionOwner battleProjection{};
  TitleMenuProducer titleMenu{};
  TitleSplashPhase titleSplash{};
  TitleMemcardInit titleMemcardInit{};
  TitleSaveCheck titleSaveCheck{};
  TitleStartupProducer titleStartup{};
  TitleMovieProducer titleMovie{};
};

// The accessor for a Core's title products; owns the cast and the missing-context refusal.
VagrantContext &contextOf(Core &core);

} // namespace vagrant
