#pragma once

#include <cstdint>
#include <span>
#include <string>
#include <vector>

class Core;

namespace vagrant::cd {

using ReadSector = std::uint32_t (*)(Core &, std::uint32_t lba, std::span<std::uint8_t> destination);
std::uint32_t readDiscSector(Core &core, std::uint32_t lba, std::span<std::uint8_t> destination);

struct SectorTransfer {
  std::vector<std::uint8_t> sectors;
  std::string detail;
  bool completed = false;

  explicit operator bool() const {
    return completed;
  }
};

// Acquire all whole sectors before a caller writes RAM or publishes executable identity.
SectorTransfer readNativeSectors(Core &core, std::uint32_t lba, std::uint32_t size, ReadSector readSector);

// Read one measured resident file extent from the real disc into guest RAM. This is the finite
// title-owned replacement for Vagrant's libds ReadN callback chain under psxport's synchronous CD
// contract; success means every requested byte was copied from the CHD. A failed read leaves guest
// RAM untouched. Code images authenticate readNativeSectors through OverlayImages before writing RAM.
bool readNativeFile(Core &core, std::uint32_t lba, std::uint32_t size, std::uint32_t destination);
bool readNativeFile(
    Core &core, std::uint32_t lba, std::uint32_t size, std::uint32_t destination, ReadSector readSector);

} // namespace vagrant::cd
