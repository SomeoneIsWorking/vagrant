#include "vagrant_runtime.h"

#include "cfg.h"
#include "config_var.h"
#include "config_vars.h"
#include "core.h"
#include "core/game_heap.h"
#include "legacy_game_interface.h"
#include "producer_db.h"
#include "render/title_menu.h"
#include "render/title_movie.h"
#include "render/title_startup.h"
#include "vagrant_context.h"

#include <cstdlib>

void vagrant_cd_register_overrides();
void vagrant_vblank_register_overrides();

namespace vagrant {

VagrantRuntime::VagrantRuntime() : LegacyGameRuntimeAdapter(legacy::measuredConfig, legacy::compatibilityHooks) {}

void *VagrantRuntime::createContext(Core &) {
  return new VagrantContext();
}

void VagrantRuntime::destroyContext(void *context) {
  delete static_cast<VagrantContext *>(context);
}

void VagrantRuntime::configureRenderPath() {
  // The project target is direct native production. Change only the default: explicit user and
  // harness selections remain higher layers on the shared CVar ladder.
  psx::config::cv_render_path.set(psx::config::Layer::Default, render_path_name(defaultRenderPath()));
}

void VagrantRuntime::registerOverrides(Game &) {
  vagrant_cd_register_overrides();
  vagrant_vblank_register_overrides();
  heap::registerHeapOverride();
  registerTitleStartupOverrides();
  registerTitleMovieOverrides();
  registerTitleMenuOverrides();
}

void VagrantRuntime::bootInit(Core &core) {
  const GameConfig *config = legacyConfigForMigration();
  if (!config || !config->gameMain) {
    cfg_loge("boot",
             "the measured RE-01 gameMain entry is absent from Vagrant Story's legacy program "
             "facts; refusing to dispatch address 0");
    std::abort();
  }
  producer_db_begin(&core);
  cfg_logi("boot", "dispatching guest main() 0x%08X on the recompiled substrate", config->gameMain);
  rec_dispatch(&core, config->gameMain);
}

} // namespace vagrant
