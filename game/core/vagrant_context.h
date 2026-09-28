#pragma once

#include "cd/libds_field.h"
#include "core/execution_telemetry.h"
#include "core/overlay_images.h"
#include "core/resident_phase.h"
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
  // The guest's own projection publication. Per-Core, because the measurement is: the title
  // re-authors its viewport every field, so nothing here may be remembered between calls.
  BattleProjectionOwner battleProjection{};
  TitleMenuProducer titleMenu{};
  TitleSplashPhase titleSplash{};
  TitleMemcardInit titleMemcardInit{};
  TitleSaveCheck titleSaveCheck{};
  TitleStartupProducer titleStartup{};
  TitleMovieProducer titleMovie{};
  // Per-Core, like every other member: nothing here may be shared between two Cores, because the
  // counters it holds are per-execution-boundary facts.
  ExecutionTelemetry executionTelemetry{};
};

// THE accessor for a Core's title products. `Core::gameCtx` is the framework's one void* slot and
// every title owner needs it, so the cast, the missing-context refusal, and its diagnostic live here
// instead of being re-derived at each call site.
VagrantContext &contextOf(Core &core);

} // namespace vagrant
