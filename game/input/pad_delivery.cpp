#include "pad_delivery.h"

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
  // Poll/replay exactly once. Vagrant's resident entry never returns to the generic native frame
  // loop, so its measured VBlank host turn owns this call.
  core.game->pad.serviceFrame();

#ifdef VAGRANT_TEST_DISABLE_PAD_NORMALIZATION
  // Negative-control seam only: retain real host polling, recording/replay, and buffer delivery but
  // withhold Vagrant's measured high-byte-first packet adaptation. Shipping builds never define it.
  return;
#endif

  const std::uint32_t fixedBuffers[] = {pad::kSlot0Buffer, pad::kSlot1Buffer};
  for (std::uint32_t slot = 0; slot < 2u; ++slot) {
    const std::uint32_t installed = core.mem_r32(pad::kDriverPointerTable + slot * pad::kDriverPointerStride);
    normalizeButtonByteOrder(core, installed ? installed : fixedBuffers[slot]);
  }
}

} // namespace vagrant
