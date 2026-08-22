#include "title_startup.h"

#include "core.h"
#include "game.h"
#include "override_registry.h"
#include "producer_scope.h"
#include "render_queue.h"
#include "vagrant_context.h"

#include <cstdlib>
#include <lucent/log.h>

#ifdef VAGRANT_HAVE_SUBSTRATE
extern void ov_title_gen_8006A778(Core *);
extern void ov_title_set_override(std::uint32_t, OverrideFn);
#endif

namespace {

// RE-12: tools/re_title_startup.py derives this unique TITLE leaf from the SHA-bound overlay. It
// super-calls DrawSync, materialises a 0x64 SPRT in the overlay's static primitive buffer, and calls
// DrawPrim with the four semantic arguments captured below.
constexpr std::uint32_t kTitleDrawSprite = 0x8006A778u;
constexpr std::size_t kSaneSpritesPerField = 4096;

vagrant::TitleStartupProducer *producer(Core &core) {
  if (!core.gameCtx) {
    return nullptr;
  }
  return &static_cast<vagrant::VagrantContext *>(core.gameCtx)->titleStartup;
}

#ifdef VAGRANT_HAVE_SUBSTRATE
void title_draw_sprite(Core *core) {
#ifdef VAGRANT_TEST_DISABLE_TITLE_PRODUCER
  // Negative-control seam only: retain the measured guest body while withholding the semantic native
  // producer. This compiles into an explicitly separate test build, never the shipping target.
  ov_title_gen_8006A778(core);
#else
  const vagrant::TitleSpriteRecipe recipe =
      vagrant::TitleSpriteRecipe::decode(core->r[4], core->r[5], core->r[6], core->r[7]);

  // Preserve TITLE's static packet-buffer writes, DrawSync, and DrawPrim side effects. The native
  // producer owns only the picture; the generated body stays linked, runnable, and oracle-selectable.
  ov_title_gen_8006A778(core);

  vagrant::TitleStartupProducer *title = producer(*core);
  if (!title) {
    lucent::error("vagrant-title", "TITLE _drawSprt reached without a VagrantContext");
    std::abort();
  }
  title->enqueue(recipe);
#endif
}
#endif

} // namespace

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

void TitleStartupProducer::present(Core &core) {
  if (pending_.empty()) {
    return;
  }

  RenderQueue &queue = core.game->activeRq();
  // _drawSprt's generated super-call executes its guest GP0 primitive before this boundary. Native mode
  // deliberately replaces that guest-origin queue item with the semantic producer below; retaining both
  // would be two renderers for one leaf and would make the producer gate meaningless.
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
  core.game->fps60.present_vk(&core);
  lucent::debug("vagrant-title", "presented {} native TITLE sprite(s)", produced);
}

void registerTitleStartupOverrides() {
#ifdef VAGRANT_HAVE_SUBSTRATE
  overrides::install(
      kTitleDrawSprite, "VagrantTitle::_drawSprt", title_draw_sprite, ov_title_gen_8006A778, ov_title_set_override);
#else
  lucent::debug("vagrant-title", "TITLE producer registration deferred: no generated substrate in this target");
#endif
}

void presentTitleStartup(Core &core) {
  TitleStartupProducer *title = producer(core);
  if (title) {
    title->present(core);
  }
}

} // namespace vagrant
