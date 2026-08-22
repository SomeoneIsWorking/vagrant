#include "title_movie.h"

#include "core.h"
#include "game.h"
#include "override_registry.h"
#include "render_queue.h"
#include "vagrant_context.h"

#include <cstdint>
#include <cstdlib>
#include <lucent/log.h>

#ifdef VAGRANT_HAVE_SUBSTRATE
extern void ov_title_gen_8006F174(Core *);
extern void ov_title_set_override(std::uint32_t, OverrideFn);
#endif

namespace {

// RE-13: tools/re_title_movie.py derives the callback and MovieData field from the SHA-bound retail
// TITLE.PRG. The intact callback uploads one decoded 24-halfword RGB24 slice through LoadImage and
// writes MovieData::frameComplete after the final slice of a 480-halfword by 224-line frame.
constexpr std::uint32_t kTitleMovieDctOutCallback = 0x8006F174u;
constexpr std::uint32_t kMovieFrameComplete = 0x800DEDDCu;

vagrant::TitleMovieProducer *producer(Core &core) {
  if (!core.gameCtx) {
    return nullptr;
  }
  return &static_cast<vagrant::VagrantContext *>(core.gameCtx)->titleMovie;
}

#ifdef VAGRANT_HAVE_SUBSTRATE
void title_movie_dct_out_callback(Core *core) {
#ifdef VAGRANT_TEST_DISABLE_TITLE_MOVIE_PRODUCER
  // Negative-control seam only: preserve guest MDEC completion, slice upload, and callback chaining
  // while withholding the semantic native scanout owner. This exists only in a separate test build.
  ov_title_gen_8006F174(core);
#else
  // The generated body remains authoritative for every guest effect. Observing frameComplete only
  // after the super-call ensures the final slice has reached guest VRAM before it becomes presentable.
  ov_title_gen_8006F174(core);
  if (core->mem_r32(kMovieFrameComplete) == 0) {
    return;
  }

  vagrant::TitleMovieProducer *movie = producer(*core);
  if (!movie) {
    lucent::error("vagrant-title-movie", "TITLE MDEC callback reached without a VagrantContext");
    std::abort();
  }
  movie->frameCompleted();
#endif
}
#endif

} // namespace

namespace vagrant {

void TitleMovieProducer::frameCompleted() {
  frameReady_ = true;
}

bool TitleMovieProducer::present(Core &core) {
  if (!frameReady_) {
    return false;
  }
  frameReady_ = false;

  // TITLE has already decoded and uploaded the frame; its own PutDispEnv selects the current display
  // origin and depth. An empty native queue is intentional here: preserveVramBackdrop makes the live
  // guest VRAM scanout the picture, and the shared presenter performs the PSX RGB24 unpack. No STR
  // bytes, decoded pixels, or canned image are duplicated on the host side.
  RenderQueue &queue = core.game->activeRq();
  queue.reset();
  queue.flush(&core);
  core.game->fps60.present_vk(&core);
  lucent::debug("vagrant-title-movie", "presented completed guest-decoded TITLE movie frame");
  return true;
}

void registerTitleMovieOverrides() {
#ifdef VAGRANT_HAVE_SUBSTRATE
  overrides::install(kTitleMovieDctOutCallback,
                     "VagrantTitleMovie::_decDCToutCallback",
                     title_movie_dct_out_callback,
                     ov_title_gen_8006F174,
                     ov_title_set_override);
#else
  lucent::debug("vagrant-title-movie", "TITLE movie registration deferred: no generated substrate in this target");
#endif
}

bool presentTitleMovie(Core &core) {
  TitleMovieProducer *movie = producer(core);
  return movie && movie->present(core);
}

} // namespace vagrant
