#include "boot/guest_rect.h"

#include "core.h"

namespace vagrant::guest {

void writeRect(Core &core, std::uint32_t address, std::int16_t x, std::int16_t y, std::int16_t w, std::int16_t h) {
  core.mem_w16(address, static_cast<std::uint16_t>(x));
  core.mem_w16(address + 2u, static_cast<std::uint16_t>(y));
  core.mem_w16(address + 4u, static_cast<std::uint16_t>(w));
  core.mem_w16(address + 6u, static_cast<std::uint16_t>(h));
}

} // namespace vagrant::guest