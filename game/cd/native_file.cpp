#include "cd/native_file.h"

#include "core.h"
#include "disc.h"
#include "game.h"
#include "overlay_router.h"

#include <algorithm>
#include <array>
#include <lucent/log.h>

namespace vagrant::cd {

bool readNativeFile(Core &core, std::uint32_t lba, std::uint32_t size, std::uint32_t destination) {
  constexpr std::uint32_t kSectorSize = 2048u;
  std::array<std::uint8_t, kSectorSize> sector{};
  std::uint32_t copied = 0u;
  while (copied < size) {
    if (!disc_read_sector(&core.game->disc, lba + copied / kSectorSize, sector.data())) {
      lucent::error("vagrant-cd",
                    "native file read failed at LBA {} after {} of {} byte(s)",
                    lba + copied / kSectorSize,
                    copied,
                    size);
      return false;
    }
    const std::uint32_t count = std::min(kSectorSize, size - copied);
    for (std::uint32_t offset = 0; offset < count; ++offset) {
      core.mem_w8(destination + copied + offset, sector[offset]);
    }
    copied += count;
  }
  overlay_note_load(&core, destination);
  lucent::debug("vagrant-cd", "native file read LBA {} size {} -> 0x{:08X}", lba, size, destination);
  return true;
}

} // namespace vagrant::cd
