#include "title_menu.h"

#include "core.h"
#include "game.h"
#include "override_registry.h"
#include "render_queue.h"
#include "vagrant_context.h"

#include <cstdint>
#include <cstdlib>
#include <lucent/log.h>

#ifdef VAGRANT_HAVE_SUBSTRATE
extern void ov_title_gen_800705AC(Core *);
extern void ov_title_set_override(std::uint32_t, OverrideFn);
#endif

namespace {

// RE-14: tools/re_title_menu.py derives the completion leaf from the SHA-bound retail TITLE.PRG.
// Each call completes one display-buffer pass after the guest has submitted its background and menu
// item DrawPrim packets; the caller reaches VSync only after this function returns.
constexpr std::uint32_t kTitleMenuItemsComplete = 0x800705ACu;

vagrant::TitleMenuProducer *producer(Core &core) {
  if (!core.gameCtx) {
    return nullptr;
  }
  return &static_cast<vagrant::VagrantContext *>(core.gameCtx)->titleMenu;
}

#ifdef VAGRANT_HAVE_SUBSTRATE
void title_menu_items_complete(Core *core) {
  // Retain the exact guest menu state updates and DrawPrim submissions. Native ownership begins only
  // at the measured completed-pass boundary.
  ov_title_gen_800705AC(core);
#ifndef VAGRANT_TEST_DISABLE_TITLE_MENU_PRODUCER
  vagrant::TitleMenuProducer *menu = producer(*core);
  if (!menu) {
    lucent::error("vagrant-title-menu", "TITLE menu pass completed without a VagrantContext");
    std::abort();
  }
  menu->frameCompleted();
#endif
}
#endif

} // namespace

namespace vagrant {

void TitleMenuProducer::frameCompleted() {
  frameReady_ = true;
}

bool TitleMenuProducer::present(Core &core) {
  if (!frameReady_) {
    return false;
  }
  frameReady_ = false;

  // The intact DrawPrim path has already translated this completed guest pass into the native queue.
  // Flush it once at the following intact VBlank and let the neutral presenter own the frame fence.
  RenderQueue &queue = core.game->activeRq();
  queue.flush(&core);
  core.game->presentation.commit(&core);
  lucent::debug("vagrant-title-menu", "presented completed TITLE menu pass");
  return true;
}

void registerTitleMenuOverrides() {
#ifdef VAGRANT_HAVE_SUBSTRATE
  overrides::install(kTitleMenuItemsComplete,
                     "VagrantTitleMenu::_drawTitleMenuItems",
                     title_menu_items_complete,
                     ov_title_gen_800705AC,
                     ov_title_set_override);
#else
  lucent::debug("vagrant-title-menu", "TITLE menu registration deferred: no generated substrate in this target");
#endif
}

bool presentTitleMenu(Core &core) {
  TitleMenuProducer *menu = producer(core);
  return menu && menu->present(core);
}

} // namespace vagrant
