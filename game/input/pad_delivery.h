#pragma once

#include <cstdint>

class Core;

namespace vagrant {

// Adapts host button state to the libpad packet layout once per native field.
class PadDelivery {
public:
  void serviceField(Core &core) const;

private:
  static void normalizeButtonByteOrder(Core &core, std::uint32_t buffer);
};

} // namespace vagrant
