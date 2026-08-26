#include "battle_frame.h"

#include "core.h"
#include "game.h"
#include "override_registry.h"
#include "render_queue.h"
#include "vagrant_context.h"

#include <cstdint>
#include <cstdlib>
#include <lucent/log.h>

#ifdef VAGRANT_HAVE_SUBSTRATE
extern void ov_battle_gen_8007629C(Core *);
extern void ov_battle_set_override(std::uint32_t, OverrideFn);
#endif

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

#ifdef VAGRANT_HAVE_SUBSTRATE
void battle_frame_complete(Core *core) {
  // Preserve the complete guest presenter. Native ownership starts only at its measured completion
  // fence, after DrawOTag has translated the dynamic guest OT into the active native queue.
  ov_battle_gen_8007629C(core);
  vagrant::BattleFrameProducer *battle = producer(*core);
  if (!battle) {
    lucent::error("vagrant-battle", "BATTLE presenter completed without a VagrantContext");
    std::abort();
  }
  battle->frameCompleted();
}
#endif

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
  core.game->presentation.commit(&core);
  lucent::debug("vagrant-battle", "presented completed BATTLE field");
  return true;
}

void registerBattleFrameOverrides() {
#ifdef VAGRANT_HAVE_SUBSTRATE
  overrides::install(kBattleFramePresenter,
                     "VagrantBattle::presentFrame",
                     battle_frame_complete,
                     ov_battle_gen_8007629C,
                     ov_battle_set_override);
#else
  lucent::debug("vagrant-battle", "BATTLE registration deferred: no generated substrate in this target");
#endif
}

bool presentBattleFrame(Core &core) {
  BattleFrameProducer *battle = producer(core);
  return battle && battle->present(core);
}

} // namespace vagrant
