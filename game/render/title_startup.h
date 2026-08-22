#pragma once

#include "title_startup_recipe.h"

#include <vector>

class Core;

namespace vagrant {

// Per-Core native producer for TITLE's immediate sprite leaf. The intact overlay uploads texture and
// CLUT data to VRAM and retains every guest write; this owner translates the leaf's semantic arguments
// into direct render-queue quads at the guest-owned VBlank boundary.
class TitleStartupProducer {
public:
  void enqueue(const TitleSpriteRecipe &sprite);
  bool present(Core &core);

  std::size_t pendingCount() const {
    return pending_.size();
  }

private:
  std::vector<TitleSpriteRecipe> pending_;
};

void registerTitleStartupOverrides();
bool presentTitleStartup(Core &core);

} // namespace vagrant
