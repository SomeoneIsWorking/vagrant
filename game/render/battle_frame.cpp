#include "battle_frame.h"

#include "core.h"
#include "game.h"
#include "render_queue.h"
#include "vagrant_context.h"

#include <cstdint>
#include <cstdlib>
#include <lucent/log.h>

namespace {

// RE-17: tools/re_frame.py derives BATTLE's sole guest frame presenter from the SHA-bound retail
// overlay. The retained body flips the resident parity word, installs the selected display/draw
// environments, and submits the caller-provided dynamic OT through DrawOTag before returning here.
constexpr std::uint32_t kBattleFramePresenter = 0x8007629Cu;

vagrant::BattleFrameProducer *producer(Core &core) {
  if (!core.gameCtx) {
    return nullptr;
  }
  return &static_cast<vagrant::VagrantContext *>(core.gameCtx)->battleFrame;
}

} // namespace

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
  BattleFrameProducer *battle = producer(core);
  return battle && battle->present(core);
}

} // namespace vagrant
