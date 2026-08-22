#pragma once

#include <cstdint>

namespace vagrant {

// Semantic arguments of TITLE's _drawSprt leaf, decoded from the guest ABI. Keeping this rule pure
// lets the unit gate exercise the exact production decoder without constructing a GPU.
struct TitleSpriteRecipe {
  int x = 0;
  int y = 0;
  int width = 0;
  int height = 0;
  int u = 0;
  int v = 0;
  int texturePageX = 0;
  int texturePageY = 0;
  int textureMode = 0;
  int clutX = 0;
  int clutY = 0;
  std::uint8_t shade = 0;

  static TitleSpriteRecipe decode(std::uint32_t xy, std::uint32_t uvClut, std::uint32_t wh, std::uint32_t tpageFade);
};

} // namespace vagrant
