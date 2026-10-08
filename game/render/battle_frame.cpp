#include "render/battle_frame.h"

#include "core.h"
#include "game.h"
#include "render_queue.h"
#include "runtime/vagrant_context.h"

#include <lucent/log.h>

namespace vagrant {

void BattleFrameProducer::frameCompleted() {
  frameReady_ = true;
}

bool BattleFrameProducer::present(Core &core) {
  if (!frameReady_) {
    return false;
  }
  frameReady_ = false;

  RenderQueue &queue = core.game->activeRq();
  queue.flush(&core);
  lucent::debug("vagrant-battle", "prepared completed BATTLE field");
  return true;
}

bool prepareBattleField(Core &core) {
  return contextOf(core).battleFrame.present(core);
}

} // namespace vagrant
