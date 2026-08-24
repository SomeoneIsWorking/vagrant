#pragma once

#include "input/pad_delivery.h"
#include "render/title_menu.h"
#include "render/title_movie.h"
#include "render/title_startup.h"

namespace vagrant {

// Title-level aggregate of cohesive per-Core products. Renderer state remains owned by its producer;
// adding another subsystem composes another member rather than growing VagrantRuntime into a god class.
struct VagrantContext {
  PadDelivery padDelivery{};
  TitleMenuProducer titleMenu{};
  TitleStartupProducer titleStartup{};
  TitleMovieProducer titleMovie{};
};

} // namespace vagrant
