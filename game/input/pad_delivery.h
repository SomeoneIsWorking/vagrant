#pragma once

#include <cstdint>

class Core;

namespace vagrant {

// Adapts psxport's host button state to Vagrant Story's measured libpad packet layout once per
// guest display field. The shared Pad remains the authority for host polling, replay, and forcing.
class PadDelivery {
public:
  void serviceField(Core &core) const;

private:
  static void normalizeButtonByteOrder(Core &core, std::uint32_t buffer);
};

} // namespace vagrant
