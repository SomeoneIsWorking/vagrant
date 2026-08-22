#pragma once

#include "render/title_startup.h"

namespace vagrant {

// Title-level aggregate of cohesive per-Core products. Renderer state remains owned by its producer;
// adding another subsystem composes another member rather than growing VagrantRuntime into a god class.
struct VagrantContext {
  TitleStartupProducer titleStartup{};
};

} // namespace vagrant
