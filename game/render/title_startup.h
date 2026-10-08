#pragma once

#include "render/title_startup_recipe.h"

#include <vector>

class Core;

namespace vagrant {

// Native producer for TITLE's immediate sprite leaf, run at the completed-field boundary.
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

bool prepareTitleStartupField(Core &core);

} // namespace vagrant
