#include "title_menu.h"

#include "core.h"
#include "game.h"
#include "render_queue.h"
#include "vagrant_context.h"

#include <cstdint>
#include <cstdlib>
#include <lucent/log.h>

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
  // Flush it once at the native field boundary; VagrantFrameDriver owns the single frame fence.
  RenderQueue &queue = core.game->activeRq();
  queue.flush(&core);
  lucent::debug("vagrant-title-menu", "prepared completed TITLE menu pass");
  return true;
}

bool prepareTitleMenuField(Core &core) {
  TitleMenuProducer *menu = producer(core);
  return menu && menu->present(core);
}

} // namespace vagrant
