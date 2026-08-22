#include "title_startup_recipe.h"

#include <cstdio>

int main() {
  // First publisher splash call in TITLE: xy=(32,88), uv=(0,0), CLUT=(320,64), 256x48,
  // 4bpp page x=320, fade=124 -> shade 4.
  const std::uint32_t xy = 32u | (88u << 16u);
  const std::uint16_t clut = static_cast<std::uint16_t>((64u << 6u) | (320u / 16u));
  const std::uint32_t uvClut = static_cast<std::uint32_t>(clut) << 16u;
  const std::uint32_t wh = 256u | (48u << 16u);
  const std::uint32_t tpageFade = 5u | (124u << 16u);
  const vagrant::TitleSpriteRecipe r = vagrant::TitleSpriteRecipe::decode(xy, uvClut, wh, tpageFade);

  if (r.x != 32 || r.y != 88 || r.width != 256 || r.height != 48 || r.u != 0 || r.v != 0 || r.texturePageX != 320 ||
      r.texturePageY != 0 || r.textureMode != 0 || r.clutX != 320 || r.clutY != 64 || r.shade != 4) {
    std::fprintf(stderr, "TITLE sprite semantic decode mismatch\n");
    return 1;
  }

  // Signed screen coordinates and over-range fade clamp are both live ABI properties, not display
  // assumptions. This is the other answer for the decoder's two non-trivial boundaries.
  const auto edge = vagrant::TitleSpriteRecipe::decode(0xFFF0FFF8u, 0u, 0x00010001u, 0x00FF0000u);
  if (edge.x != -8 || edge.y != -16 || edge.shade != 0) {
    std::fprintf(stderr, "TITLE sprite signed-coordinate/fade boundary mismatch\n");
    return 1;
  }

  std::puts("TITLE startup sprite recipe: semantic ABI decode PASS");
  return 0;
}
