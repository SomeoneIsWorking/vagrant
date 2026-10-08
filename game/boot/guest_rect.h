#pragma once

#include <cstdint>

class Core;

namespace vagrant::guest {

// Writes a PSX RECT (four little-endian int16 at +0/+2/+4/+6) into guest RAM.
void writeRect(Core &core, std::uint32_t address, std::int16_t x, std::int16_t y, std::int16_t w, std::int16_t h);

} // namespace vagrant::guest