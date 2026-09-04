#include "title_movie.h"

#include "core.h"
#include "game.h"
#include "render_queue.h"
#include "vagrant_context.h"

#include <cstdint>
#include <cstdlib>
#include <lucent/log.h>

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
  lucent::debug("vagrant-title-movie", "prepared completed guest-decoded TITLE movie frame");
  return true;
}

bool prepareTitleMovieField(Core &core) {
  TitleMovieProducer *movie = producer(core);
  return movie && movie->present(core);
}

} // namespace vagrant
