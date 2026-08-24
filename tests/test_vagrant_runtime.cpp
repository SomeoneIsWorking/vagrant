#include "config_var.h"
#include "config_vars.h"
#include "core.h"
#include "game.h"
#include "game_iface.h"
#include "vagrant_context.h"
#include "vagrant_runtime.h"

#include <cstdio>
#include <memory>
#include <type_traits>

namespace {
int g_cdRegistrations = 0;
int g_vblankRegistrations = 0;
} // namespace

void vagrant_cd_register_overrides() {
  ++g_cdRegistrations;
}

void vagrant_vblank_register_overrides() {
  ++g_vblankRegistrations;
}

int main() {
  static_assert(std::is_base_of_v<GameRuntime, vagrant::VagrantRuntime>);
  static_assert(std::is_base_of_v<LegacyGameRuntimeAdapter, vagrant::VagrantRuntime>);
  static_assert(vagrant::VagrantRuntime::defaultRenderPath() == RenderPath::Native);

  vagrant::VagrantRuntime runtime;
  psx::config::cv_render_path.set(psx::config::Layer::Default, "gte");
  runtime.configureRenderPath();
  if (psx::config::render_path() != RenderPath::Native) {
    std::fprintf(stderr, "VagrantRuntime did not install the direct-native project default\n");
    return 1;
  }
  psxport_install_game(runtime);
  auto game = std::make_unique<Game>();
  const GameHooks *legacyHooks = runtime.legacyHooksForMigration();
  if (psxport_game_runtime() != &runtime || game->core.runtime != &runtime ||
      runtime.legacyConfigForMigration() == nullptr || legacyHooks == nullptr || game->core.gameCtx == nullptr) {
    std::fprintf(stderr, "VagrantRuntime did not own the installed compatibility seam\n");
    return 1;
  }
  if (legacyHooks->bootInit != nullptr || legacyHooks->registerOverrides != nullptr) {
    std::fprintf(stderr, "boot or override ownership remained in legacy GameHooks\n");
    return 1;
  }

  auto *context = static_cast<vagrant::VagrantContext *>(game->core.gameCtx);
  context->titleMovie.frameCompleted();
  if (!context->titleMovie.frameReady()) {
    std::fprintf(stderr, "VagrantContext did not retain TITLE movie producer state\n");
    return 1;
  }
  context->titleMenu.frameCompleted();
  if (!context->titleMenu.frameReady()) {
    std::fprintf(stderr, "VagrantContext did not retain TITLE menu producer state\n");
    return 1;
  }

  runtime.registerOverrides(*game);
  if (g_cdRegistrations != 1 || g_vblankRegistrations != 1) {
    std::fprintf(stderr, "VagrantRuntime did not compose both measured override owners\n");
    return 1;
  }

  std::puts("VagrantRuntime: derived install, measured legacy facts, owned boot/overrides");
  return 0;
}
