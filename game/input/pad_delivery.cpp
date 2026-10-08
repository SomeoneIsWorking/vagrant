#include "input/pad_delivery.h"

#include "core.h"
#include "game.h"
#include "input/pad_facts.h"

namespace vagrant {

void PadDelivery::normalizeButtonByteOrder(Core &core, std::uint32_t buffer) {
  const std::uint8_t first = core.mem_r8(buffer + 2u);
  const std::uint8_t second = core.mem_r8(buffer + 3u);
  core.mem_w8(buffer + 2u, second);
  core.mem_w8(buffer + 3u, first);
}

void PadDelivery::serviceField(Core &core) const {
  // Once per native-owned field boundary.
  core.game->pad.serviceFrame();

#ifdef VAGRANT_TEST_DISABLE_PAD_NORMALIZATION
  // Negative-control seam: skips the packet adaptation.
  return;
#endif

  const std::uint32_t fixedBuffers[] = {pad::kSlot0Buffer, pad::kSlot1Buffer};
  for (std::uint32_t slot = 0; slot < 2u; ++slot) {
    const std::uint32_t installed = core.mem_r32(pad::kDriverPointerTable + slot * pad::kDriverPointerStride);
    normalizeButtonByteOrder(core, installed ? installed : fixedBuffers[slot]);
  }
}

} // namespace vagrant
