#include "render/title_menu.h"

#include "core.h"
#include "game.h"
#include "render_queue.h"
#include "runtime/vagrant_context.h"

#include <lucent/log.h>

namespace vagrant {

void TitleMenuProducer::frameCompleted() {
  frameReady_ = true;
}

bool TitleMenuProducer::present(Core &core) {
  if (!frameReady_) {
    return false;
  }
  frameReady_ = false;

  // Flush the translated guest pass once; VagrantFrameDriver owns the frame fence.
  RenderQueue &queue = core.game->activeRq();
  queue.flush(&core);
  lucent::debug("vagrant-title-menu", "prepared completed TITLE menu pass");
  return true;
}

bool prepareTitleMenuField(Core &core) {
  return contextOf(core).titleMenu.present(core);
}

} // namespace vagrant
