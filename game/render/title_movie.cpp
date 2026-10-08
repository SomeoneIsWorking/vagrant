#include "render/title_movie.h"

#include "core.h"
#include "game.h"
#include "render_queue.h"
#include "runtime/vagrant_context.h"

#include <lucent/log.h>

namespace vagrant {

void TitleMovieProducer::frameCompleted() {
  frameReady_ = true;
}

bool TitleMovieProducer::present(Core &core) {
  if (!frameReady_) {
    return false;
  }
  frameReady_ = false;

  // The queue is empty on purpose: preserveVramBackdrop makes guest VRAM the picture.
  RenderQueue &queue = core.game->activeRq();
  queue.reset();
  queue.flush(&core);
  lucent::debug("vagrant-title-movie", "prepared completed guest-decoded TITLE movie frame");
  return true;
}

bool prepareTitleMovieField(Core &core) {
  return contextOf(core).titleMovie.present(core);
}

} // namespace vagrant
