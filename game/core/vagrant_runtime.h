#pragma once

#include "game_iface.h"
#include "render_mode.h"

namespace vagrant {

// Process-lifetime owner of Vagrant Story's framework-facing behavior. The legacy base is bounded
// migration debt: generic psxport algorithms still consume measured configuration groups and the
// native frame/scheduler paths still use compatibility callbacks.
class VagrantRuntime final : public LegacyGameRuntimeAdapter {
public:
  VagrantRuntime();

  void configureRenderPath();

  static constexpr RenderPath defaultRenderPath() {
    return RenderPath::Native;
  }

  void *createContext(Core &core) override;
  void destroyContext(void *context) override;
  void registerOverrides(Game &game) override;
  void bootInit(Core &core) override;
};

} // namespace vagrant
