#include "core.h"
#include "disc.h"
#include "game.h"
#include "lightrec_executor.h"
#include "lucent/content.h"
#include "overlay_images.h"
#include "vagrant_runtime.h"

#include <algorithm>
#include <array>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iterator>
#include <memory>
#include <span>
#include <string>
#include <string_view>
#include <tuple>
#include <vector>

namespace {

using vagrant::OverlayKind;
using vagrant::OverlaySpec;

std::vector<std::uint8_t> guestReturn(std::uint32_t value) {
  std::vector<std::uint8_t> bytes(12, 0);
  const std::array<std::uint32_t, 3> words{0x24020000u | value, 0x03e00008u, 0u};
  std::memcpy(bytes.data(), words.data(), bytes.size());
  return bytes;
}

std::string sha256(std::span<const std::uint8_t> bytes) {
  return lucent::content::sha256_hex(
      lucent::content::sha256({reinterpret_cast<const std::byte *>(bytes.data()), bytes.size()}));
}

bool require(bool condition, const char *message) {
  if (!condition) {
    std::fprintf(stderr, "%s\n", message);
  }
  return condition;
}

std::vector<std::uint8_t> readFile(const std::filesystem::path &path) {
  std::ifstream stream(path, std::ios::binary);
  return {std::istreambuf_iterator<char>(stream), std::istreambuf_iterator<char>()};
}

bool retailInputs(const std::filesystem::path &directory, bool discTransfer) {
  vagrant::VagrantRuntime runtime;
  psxport_install_game(runtime);
  auto game = std::make_unique<Game>();
  vagrant::OverlayImages overlays(game->core);
  for (const auto [kind, stem, isoPath, entry, guestBase] : {
           std::tuple{OverlayKind::Title, "TITLE", "TITLE/TITLE.PRG", 0x80071334u, 0x80068800u},
           std::tuple{OverlayKind::Battle, "BATTLE", "BATTLE/BATTLE.PRG", 0x800798A4u, 0x80068800u},
           std::tuple{OverlayKind::InitBattle, "INITBTL", "BATTLE/INITBTL.PRG", 0x800FA35Cu, 0x800F9800u},
       }) {
    const auto path = directory / (std::string(stem) + (discTransfer ? ".PRG" : ".BIN"));
    if (!require(std::filesystem::is_regular_file(path), "retail overlay input is missing")) {
      return false;
    }
    const auto bytes = readFile(path);
    vagrant::OverlayLoadResult loaded;
    if (discTransfer) {
      std::uint32_t lba = 0u;
      std::uint32_t fileBytes = 0u;
      if (!require(disc_find_file(&game->disc, isoPath, &lba, &fileBytes) && fileBytes == bytes.size(),
                   "retail CD directory differs from the authenticated overlay file")) {
        return false;
      }
      std::vector<std::uint8_t> sectors(((bytes.size() + 2047u) / 2048u) * 2048u);
      for (std::size_t offset = 0; offset < sectors.size(); offset += 2048u) {
        if (!require(disc_read_sector(
                         &game->disc, lba + static_cast<std::uint32_t>(offset / 2048u), sectors.data() + offset),
                     "retail CD sector read failed")) {
          return false;
        }
      }
      if (!require(std::equal(bytes.begin(), bytes.end(), sectors.begin()),
                   "retail CD transfer differs from the authenticated overlay file")) {
        return false;
      }
      auto changedTail = sectors;
      changedTail.back() ^= 1u;
      if (!require(!overlays.loadTransfer(kind, changedTail), "changed final-sector padding was admitted")) {
        return false;
      }
      const auto physical = guestBase & 0x1fffffffu;
      std::copy(changedTail.begin(), changedTail.end(), game->core.ram + physical);
      if (!require(!overlays.adoptTransfer(kind), "changed resident final-sector padding was admitted")) {
        return false;
      }
      std::copy(sectors.begin(), sectors.end(), game->core.ram + physical);
      loaded = overlays.adoptTransfer(kind);
    } else {
      loaded = overlays.load(kind, bytes);
    }
    if (!require(static_cast<bool>(loaded), "authenticated retail overlay was refused") ||
        !require(game->core.currentImageIdentity(entry) == loaded.identity,
                 "retail overlay entry does not resolve to its image generation")) {
      return false;
    }
  }
  auto altered = readFile(directory / (discTransfer ? "TITLE.PRG" : "TITLE.BIN"));
  altered[0] ^= 1u;
  if (!require(!overlays.load(OverlayKind::Title, altered), "altered retail TITLE image was admitted")) {
    return false;
  }
  std::printf("retail overlay admission: 3/3 exact images accepted; changed TITLE 1/1 refused; "
              "disc transfer tails %s\n",
              discTransfer ? "3/3 adopted from RAM and 3/3 changed refused" : "not requested");
  return true;
}

bool syntheticReplacement() {
  const auto title = guestReturn(7);
  std::vector<std::uint8_t> titleTransfer(2048u, 0u);
  std::copy(title.begin(), title.end(), titleTransfer.begin());
  auto battle = guestReturn(19);
  battle.resize(16, 0);
  const auto init = guestReturn(31);
  const std::array<OverlaySpec, 3> specs{{
      {OverlayKind::Title, "TITLE.PRG", 0x80068800u, title.size(), sha256(title)},
      {OverlayKind::Battle, "BATTLE.PRG", 0x80068800u, battle.size(), sha256(battle)},
      {OverlayKind::InitBattle, "INITBTL.PRG", 0x800F9800u, init.size(), sha256(init)},
  }};
  vagrant::VagrantRuntime runtime;
  psxport_install_game(runtime);
  auto game = std::make_unique<Game>();
  auto &core = game->core;
  vagrant::OverlayImages overlays(core, specs);
  core.pc = 0x8001F544u;
  core.r[31] = 0x8001F548u;
  const auto foreign = core.imageCatalog().activate("foreign", {0x68800u, 0x6880Cu}, 1u);
  if (!require(!overlays.load(OverlayKind::Title, title), "foreign overlay residency was overwritten") ||
      !require(core.currentImageIdentity(0x80068800u) == foreign, "foreign residency was changed") ||
      !require(core.imageCatalog().deactivate(foreign), "foreign fixture could not be retired")) {
    return false;
  }
  const auto foreignTail = core.imageCatalog().activate("foreign-tail", {0x6880Cu, 0x68810u}, 2u);
  if (!require(!overlays.loadTransfer(OverlayKind::Title, titleTransfer),
               "foreign final-sector residency was overwritten") ||
      !require(core.currentImageIdentity(0x8006880Cu) == foreignTail, "foreign tail residency was changed") ||
      !require(core.imageCatalog().deactivate(foreignTail), "foreign tail fixture could not be retired")) {
    return false;
  }
  core.mem_w8(0x8006880Cu, 0xA5u);
  core.mem_w8(0x80068FFFu, 0xA5u);
  auto changedTail = titleTransfer;
  changedTail.back() = 1u;
  if (!require(!overlays.loadTransfer(OverlayKind::Title, changedTail), "changed sector tail was admitted") ||
      !require(core.ram[0x6880Cu] == 0xA5u && core.ram[0x68FFFu] == 0xA5u, "refused sector transfer changed RAM")) {
    return false;
  }
  const auto first = overlays.loadTransfer(OverlayKind::Title, titleTransfer);
  if (!require(static_cast<bool>(first), "synthetic TITLE image was refused") ||
      !require(core.ram[0x6880Cu] == 0u && core.ram[0x68FFFu] == 0u, "completed sector tail was not copied into RAM") ||
      !require(!core.currentImageIdentity(0x8006880Cu), "sector padding became an executable image") ||
      !require(core.pc == 0x8001F544u, "overlay load changed the resident PC") ||
      !require(core.currentImageIdentity(0x80068800u) == first.identity,
               "TITLE slot did not resolve to its first image generation")) {
    return false;
  }
  const auto initialInvalidations = core.lightrecExecutor().counters().invalidations;
  if (!require(core.lightrecExecutor()
                   .executeFunction(0x80068800u, core.r[31], psx::cpu::ExecutionBudget::fromCycles(100))
                   .returned(),
               "TITLE synthetic block did not execute through Lightrec") ||
      !require(core.r[2] == 7u, "TITLE translated block returned the wrong value") ||
      !require(core.lightrecExecutor().counters().executedBlocks > 0u, "TITLE executed zero translated blocks")) {
    return false;
  }
  auto altered = title;
  altered[0] ^= 1u;
  const auto rejected = overlays.load(OverlayKind::Title, altered);
  if (!require(!rejected, "changed TITLE payload was admitted") ||
      !require(core.currentImageIdentity(0x80068800u) == first.identity,
               "failed replacement changed TITLE residency") ||
      !require(core.ram[0x68800u] == title[0], "failed replacement changed RAM") ||
      !require(core.lightrecExecutor().counters().invalidations == initialInvalidations,
               "failed replacement invalidated translated code")) {
    return false;
  }
  const auto second = overlays.load(OverlayKind::Battle, battle);
  if (!require(static_cast<bool>(second), "BATTLE replacement was refused") ||
      !require(second.identity != first.identity, "reused overlay image generation") ||
      !require(core.currentImageIdentity(0x80068800u) == second.identity, "BATTLE did not replace TITLE slot") ||
      !require(core.imageCatalog().activeCount() == 1u, "retired TITLE image remained active") ||
      !require(core.lightrecExecutor().counters().invalidations > initialInvalidations,
               "BATTLE replacement did not invalidate translated code") ||
      !require(core.lightrecExecutor()
                   .executeFunction(0x80068800u, core.r[31], psx::cpu::ExecutionBudget::fromCycles(100))
                   .returned(),
               "BATTLE replacement did not execute through Lightrec") ||
      !require(core.r[2] == 19u, "stale TITLE translation survived BATTLE replacement") ||
      !require(core.lightrecExecutor().counters().fallback.calls == 0u,
               "synthetic overlay execution entered the interpreter")) {
    return false;
  }
  const auto separate = overlays.load(OverlayKind::InitBattle, init);
  if (!require(static_cast<bool>(separate), "INITBTL image was refused") ||
      !require(core.currentImageIdentity(0x800F9800u) == separate.identity, "INITBTL did not occupy its own slot") ||
      !require(core.currentImageIdentity(0x80068800u) == second.identity, "INITBTL disturbed the BATTLE slot") ||
      !require(core.imageCatalog().activeCount() == 2u, "overlay slot active count is wrong")) {
    return false;
  }
  const auto shorter = overlays.load(OverlayKind::Title, title);
  return require(static_cast<bool>(shorter), "TITLE reload was refused") &&
         require(core.currentImageIdentity(0x80068800u) == shorter.identity, "TITLE reload did not replace BATTLE") &&
         require(!core.currentImageIdentity(0x8006880Cu),
                 "retired BATTLE tail stayed executable after shorter TITLE load") &&
         require(core.currentImageIdentity(0x800F9800u) == separate.identity,
                 "TITLE reload disturbed INITBTL residency");
}

bool syntheticAdoption() {
  const auto title = guestReturn(7);
  const auto battle = guestReturn(19);
  std::vector<std::uint8_t> titleTransfer(2048u, 0u);
  std::vector<std::uint8_t> battleTransfer(2048u, 0u);
  std::copy(title.begin(), title.end(), titleTransfer.begin());
  std::copy(battle.begin(), battle.end(), battleTransfer.begin());
  const std::array<OverlaySpec, 3> specs{{
      {OverlayKind::Title, "TITLE.PRG", 0x80068800u, title.size(), sha256(title)},
      {OverlayKind::Battle, "BATTLE.PRG", 0x80068800u, battle.size(), sha256(battle)},
      {OverlayKind::InitBattle, "INITBTL.PRG", 0x800F9800u, 4u, sha256(std::array<std::uint8_t, 4>{})},
  }};
  vagrant::VagrantRuntime runtime;
  psxport_install_game(runtime);
  auto game = std::make_unique<Game>();
  auto &core = game->core;
  vagrant::OverlayImages overlays(core, specs);
  core.r[31] = 0x8001F548u;
  std::copy(titleTransfer.begin(), titleTransfer.end(), core.ram + 0x68800u);
  core.ram[0x68FFFu] = 1u;
  if (!require(!overlays.adoptTransfer(OverlayKind::Title), "resident transfer with changed padding was admitted") ||
      !require(core.imageCatalog().activeCount() == 0u, "refused resident transfer published an image")) {
    return false;
  }
  core.ram[0x68FFFu] = 0u;
  core.ram[0x68800u] ^= 1u;
  if (!require(!overlays.adoptTransfer(OverlayKind::Title), "resident transfer with changed payload was admitted") ||
      !require(core.imageCatalog().activeCount() == 0u, "changed resident payload published an image")) {
    return false;
  }
  core.ram[0x68800u] ^= 1u;
  const auto foreignTail = core.imageCatalog().activate("foreign-tail", {0x6880Cu, 0x68810u}, 2u);
  if (!require(!overlays.adoptTransfer(OverlayKind::Title), "foreign resident tail was overwritten") ||
      !require(core.currentImageIdentity(0x8006880Cu) == foreignTail, "foreign resident tail changed") ||
      !require(core.imageCatalog().deactivate(foreignTail), "foreign resident tail could not be retired")) {
    return false;
  }
  const auto first = overlays.adoptTransfer(OverlayKind::Title);
  if (!require(static_cast<bool>(first), "completed resident TITLE transfer was refused") ||
      !require(core.currentImageIdentity(0x80068800u) == first.identity, "resident TITLE identity is absent") ||
      !require(!core.currentImageIdentity(0x8006880Cu), "resident TITLE padding became executable") ||
      !require(core.lightrecExecutor()
                   .executeFunction(0x80068800u, core.r[31], psx::cpu::ExecutionBudget::fromCycles(100))
                   .returned(),
               "resident TITLE block did not execute through Lightrec") ||
      !require(core.r[2] == 7u, "resident TITLE block returned the wrong value")) {
    return false;
  }
  const auto invalidations = core.lightrecExecutor().counters().invalidations;
  std::copy(battleTransfer.begin(), battleTransfer.end(), core.ram + 0x68800u);
  core.ram[0x68FFFu] = 1u;
  if (!require(!overlays.adoptTransfer(OverlayKind::Battle),
               "resident BATTLE transfer with changed padding was admitted") ||
      !require(core.currentImageIdentity(0x80068800u) == first.identity,
               "refused resident replacement changed image generation") ||
      !require(core.lightrecExecutor().counters().invalidations == invalidations,
               "refused resident replacement invalidated translated code")) {
    return false;
  }
  core.ram[0x68FFFu] = 0u;
  const auto second = overlays.adoptTransfer(OverlayKind::Battle);
  return require(static_cast<bool>(second), "completed resident BATTLE transfer was refused") &&
         require(second.identity != first.identity, "resident replacement reused the old generation") &&
         require(core.currentImageIdentity(0x80068800u) == second.identity, "resident BATTLE did not replace TITLE") &&
         require(core.lightrecExecutor().counters().invalidations > invalidations,
                 "resident BATTLE replacement did not invalidate translated code") &&
         require(core.lightrecExecutor()
                     .executeFunction(0x80068800u, core.r[31], psx::cpu::ExecutionBudget::fromCycles(100))
                     .returned(),
                 "resident BATTLE replacement did not execute through Lightrec") &&
         require(core.r[2] == 19u, "stale TITLE translation survived resident BATTLE replacement") &&
         require(core.lightrecExecutor().counters().fallback.calls == 0u,
                 "resident overlay execution entered the interpreter");
}

} // namespace

int main(int argc, char **argv) {
  if (!syntheticReplacement() || !syntheticAdoption()) {
    return 1;
  }
  if (argc == 3 && std::string_view(argv[1]) == "--retail-input-dir") {
    return retailInputs(argv[2], false) ? 0 : 1;
  }
  if (argc == 3 && std::string_view(argv[1]) == "--retail-disc-input-dir") {
    return retailInputs(argv[2], true) ? 0 : 1;
  }
  return require(argc == 1,
                 "usage: vagrant_overlay_images [--retail-input-dir DIRECTORY | "
                 "--retail-disc-input-dir DIRECTORY]")
             ? 0
             : 2;
}
