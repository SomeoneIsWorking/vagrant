#include "cd/native_file.h"
#include "core.h"
#include "core/resident_facts.h"
#include "core/title_transfer.h"
#include "game.h"
#include "lucent/content.h"

#include <algorithm>
#include <array>
#include <cstdint>
#include <cstdio>
#include <memory>
#include <span>
#include <vector>

namespace {

constexpr std::size_t kSectorBytes = 2048u;
constexpr std::size_t kRetailTitleImageBytes = 554568u;
constexpr std::size_t kFinalPayloadBytes = kRetailTitleImageBytes % kSectorBytes;
std::vector<std::uint8_t> *g_transfer = nullptr;
bool g_shortFinalSector = false;
std::uint32_t g_sectorReads = 0u;

std::uint32_t readSector(Core &, std::uint32_t lba, std::span<std::uint8_t> destination) {
  auto index = lba - vagrant::resident::kTitlePrgLba;
  if (!g_transfer || index >= g_transfer->size() / kSectorBytes) {
    return 0u;
  }
  ++g_sectorReads;
  std::size_t offset = index * kSectorBytes;
  std::size_t delivered =
      g_shortFinalSector && offset + kSectorBytes == g_transfer->size() ? kFinalPayloadBytes : kSectorBytes;
  std::copy_n(g_transfer->data() + offset, delivered, destination.data());
  return static_cast<std::uint32_t>(delivered);
}

bool require(bool condition, const char *message) {
  if (!condition) {
    std::fprintf(stderr, "%s\n", message);
  }
  return condition;
}

} // namespace

int main() {
  auto game = std::make_unique<Game>();
  auto &core = game->core;
  std::vector<std::uint8_t> sectors(vagrant::resident::kTitlePrgSize, 0u);
  for (std::size_t offset = 0; offset < kRetailTitleImageBytes; ++offset) {
    sectors[offset] = static_cast<std::uint8_t>((offset * 37u + 19u) & 0xffu);
  }
  g_transfer = &sectors;
  auto digest = lucent::content::sha256_hex(
      lucent::content::sha256({reinterpret_cast<const std::byte *>(sectors.data()), kRetailTitleImageBytes}));
  std::array<vagrant::OverlaySpec, 3> specs{{
      {vagrant::OverlayKind::Title, "TITLE.PRG", vagrant::resident::kTitleOverlayBase, kRetailTitleImageBytes, digest},
      {vagrant::OverlayKind::Battle, "BATTLE.PRG", 0x80068800u, 4u, digest},
      {vagrant::OverlayKind::InitBattle, "INITBTL.PRG", 0x800F9800u, 4u, digest},
  }};
  vagrant::OverlayImages overlays(core, std::move(specs));
  auto physical = vagrant::resident::kTitleOverlayBase & 0x1fffffffu;

  // A matching RAM image does not prove the latest requested transfer completed.
  std::copy(sectors.begin(), sectors.end(), core.ram + physical);
  g_shortFinalSector = true;
  auto incomplete = vagrant::readAndLoadTitle(core, overlays, readSector);
  if (!require(!incomplete, "short final sector was published") ||
      !require(g_sectorReads == sectors.size() / kSectorBytes, "short transfer did not reach its final sector") ||
      !require(!core.currentImageIdentity(vagrant::resident::kTitleEntry),
               "incomplete transfer gained TITLE identity")) {
    return 1;
  }

  core.ram[physical] ^= 0xffu;
  g_shortFinalSector = false;
  g_sectorReads = 0u;
  auto completed = vagrant::readAndLoadTitle(core, overlays, readSector);
  if (!require(static_cast<bool>(completed), "complete TITLE transfer was refused") ||
      !require(g_sectorReads == sectors.size() / kSectorBytes, "complete transfer skipped a sector") ||
      !require(core.currentImageIdentity(vagrant::resident::kTitleEntry) == completed.identity,
               "completed transfer did not publish TITLE entry") ||
      !require(std::equal(sectors.begin(), sectors.end(), core.ram + physical),
               "completed transfer changed sector bytes")) {
    return 1;
  }

  sectors[0] ^= 1u;
  g_sectorReads = 0u;
  auto wrongImage = vagrant::readAndLoadTitle(core, overlays, readSector);
  if (!require(!wrongImage, "complete altered TITLE payload was published") ||
      !require(g_sectorReads == sectors.size() / kSectorBytes, "altered transfer did not complete all sectors") ||
      !require(core.currentImageIdentity(vagrant::resident::kTitleEntry) == completed.identity,
               "altered replacement displaced the prior TITLE generation") ||
      !require(core.ram[physical] != sectors[0], "altered replacement changed RAM under the prior identity")) {
    return 1;
  }

  g_shortFinalSector = true;
  g_sectorReads = 0u;
  auto failedReplacement = vagrant::readAndLoadTitle(core, overlays, readSector);
  if (!require(!failedReplacement, "short replacement was published") ||
      !require(core.currentImageIdentity(vagrant::resident::kTitleEntry) == completed.identity,
               "short replacement displaced the prior TITLE generation") ||
      !require(core.ram[physical] != sectors[0], "short replacement changed RAM under the prior identity")) {
    return 1;
  }
  std::puts("TITLE transfer: 271/271 sectors publish; short and altered replacements preserve RAM and identity");
  return 0;
}
