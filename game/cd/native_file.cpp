#include "cd/native_file.h"

#include "core.h"
#include "disc.h"
#include "game.h"

#include <algorithm>
#include <array>
#include <limits>
#include <lucent/log.h>
#include <utility>

namespace vagrant::cd {
namespace {

constexpr std::uint32_t kSectorSize = 2048u;

} // namespace

std::uint32_t readDiscSector(Core &core, std::uint32_t lba, std::span<std::uint8_t> destination) {
  if (destination.size() != kSectorSize) {
    return 0u;
  }
  return disc_read_sector(&core.game->disc, lba, destination.data()) ? kSectorSize : 0u;
}

bool readNativeFile(Core &core, std::uint32_t lba, std::uint32_t size, std::uint32_t destination) {
  return readNativeFile(core, lba, size, destination, readDiscSector);
}

SectorTransfer readNativeSectors(Core &core, std::uint32_t lba, std::uint32_t size, ReadSector readSector) {
  if (!readSector) {
    return {{}, "native file read has no sector provider", false};
  }
  if (size > std::numeric_limits<std::uint32_t>::max() - (kSectorSize - 1u)) {
    return {{}, "native file read size overflows whole-sector extent", false};
  }
  std::array<std::uint8_t, kSectorSize> sector{};
  std::size_t transferBytes = ((static_cast<std::size_t>(size) + kSectorSize - 1u) / kSectorSize) * kSectorSize;
  std::vector<std::uint8_t> sectors(transferBytes);
  std::uint32_t copied = 0u;
  while (copied < size) {
    if (readSector(core, lba + copied / kSectorSize, sector) != kSectorSize) {
      return {{},
              "native file read did not complete a whole sector at LBA " + std::to_string(lba + copied / kSectorSize) +
                  " after " + std::to_string(copied) + " of " + std::to_string(size) + " byte(s)",
              false};
    }
    std::copy(sector.begin(), sector.end(), sectors.begin() + copied);
    copied += kSectorSize;
  }
  return {std::move(sectors), {}, true};
}

bool readNativeFile(
    Core &core, std::uint32_t lba, std::uint32_t size, std::uint32_t destination, ReadSector readSector) {
  auto transfer = readNativeSectors(core, lba, size, readSector);
  if (!transfer) {
    lucent::error("vagrant-cd", "{}", transfer.detail);
    return false;
  }
  for (std::uint32_t offset = 0; offset < size; ++offset) {
    core.mem_w8(destination + offset, transfer.sectors[offset]);
  }
  lucent::debug("vagrant-cd", "native file read LBA {} size {} -> 0x{:08X}", lba, size, destination);
  return true;
}

} // namespace vagrant::cd
