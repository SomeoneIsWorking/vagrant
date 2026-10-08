#include "render/title_startup.h"

#include "core.h"
#include "game.h"
#include "producer_scope.h"
#include "render_queue.h"
#include "runtime/vagrant_context.h"

#include <cstdlib>
#include <lucent/log.h>

// TITLE leaf that builds a 0x64 SPRT in the overlay's primitive buffer and calls DrawPrim.
constexpr std::uint32_t kTitleDrawSprite = 0x8006A778u;
constexpr std::size_t kSaneSpritesPerField = 4096;

namespace vagrant {

void TitleStartupProducer::enqueue(const TitleSpriteRecipe &sprite) {
  if (pending_.size() >= kSaneSpritesPerField) {
    lucent::error("vagrant-title",
                  "TITLE emitted more than {} immediate sprites in one field; refusing a runaway producer",
                  kSaneSpritesPerField);
    std::abort();
  }
  pending_.push_back(sprite);
}

bool TitleStartupProducer::present(Core &core) {
  if (pending_.empty()) {
    return false;
  }

  RenderQueue &queue = core.game->activeRq();
  // Native presentation replaces the guest-origin item; keeping both would draw the leaf twice.
  queue.reset();
  const GpuState &gpu = core.game->gpu;
  {
    ProducerScope scope(&core.rsub.producerScope, kTitleDrawSprite, "VagrantTitle::_drawSprt");
    for (const TitleSpriteRecipe &sprite : pending_) {
      const int x1 = sprite.x + sprite.width;
      const int y1 = sprite.y + sprite.height;
      const int u1 = sprite.u + sprite.width;
      const int v1 = sprite.v + sprite.height;
      const int xs[4] = {sprite.x, x1, sprite.x, x1};
      const int ys[4] = {sprite.y, sprite.y, y1, y1};
      const int us[4] = {sprite.u, u1, sprite.u, u1};
      const int vs[4] = {sprite.v, sprite.v, v1, v1};
      const unsigned char shade[4] = {sprite.shade, sprite.shade, sprite.shade, sprite.shade};

      queue.push2dQuad(RQ_OVERLAY,
                       /*order_2d_fg=*/1,
                       xs,
                       ys,
                       us,
                       vs,
                       shade,
                       shade,
                       shade,
                       sprite.texturePageX,
                       sprite.texturePageY,
                       sprite.textureMode,
                       /*raw=*/0,
                       sprite.clutX,
                       sprite.clutY,
                       gpu.s_tw_mx,
                       gpu.s_tw_my,
                       gpu.s_tw_ox,
                       gpu.s_tw_oy,
                       gpu.s_da_x0,
                       gpu.s_da_y0,
                       gpu.s_da_x1,
                       gpu.s_da_y1,
                       /*semi=*/0);
    }
  }

  const std::size_t produced = pending_.size();
  pending_.clear();
  queue.flush(&core);
  lucent::debug("vagrant-title", "prepared {} native TITLE sprite(s)", produced);
  return true;
}

bool prepareTitleStartupField(Core &core) {
  return contextOf(core).titleStartup.present(core);
}

} // namespace vagrant
