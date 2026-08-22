#include "title_startup_recipe.h"

#include <algorithm>

namespace vagrant {

TitleSpriteRecipe
TitleSpriteRecipe::decode(std::uint32_t xy, std::uint32_t uvClut, std::uint32_t wh, std::uint32_t tpageFade) {
  TitleSpriteRecipe recipe;
  recipe.x = static_cast<std::int16_t>(xy & 0xFFFFu);
  recipe.y = static_cast<std::int16_t>(xy >> 16u);
  recipe.width = static_cast<int>(wh & 0xFFFFu);
  recipe.height = static_cast<int>(wh >> 16u);
  recipe.u = static_cast<int>(uvClut & 0xFFu);
  recipe.v = static_cast<int>((uvClut >> 8u) & 0xFFu);

  const std::uint16_t clut = static_cast<std::uint16_t>(uvClut >> 16u);
  recipe.clutX = static_cast<int>(clut & 0x3Fu) * 16;
  recipe.clutY = static_cast<int>((clut >> 6u) & 0x1FFu);

  const std::uint16_t tpage = static_cast<std::uint16_t>(tpageFade & 0x9FFu);
  recipe.texturePageX = static_cast<int>(tpage & 0xFu) * 64;
  recipe.texturePageY = static_cast<int>((tpage >> 4u) & 1u) * 256;
  recipe.textureMode = static_cast<int>((tpage >> 7u) & 3u);

  const int fade = static_cast<int>(tpageFade >> 16u);
  recipe.shade = static_cast<std::uint8_t>(std::clamp(0x80 - fade, 0, 0xFF));
  return recipe;
}

} // namespace vagrant
