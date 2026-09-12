#include "core.h"
#include "game.h"
#include "lightrec_executor.h"
#include "lucent/content.h"
#include "overlay_images.h"
#include "resident_facts.h"
#include "title_entry.h"
#include "vagrant_runtime.h"

#include <algorithm>
#include <array>
#include <cstdint>
#include <cstdio>
#include <filesystem>
#include <fstream>
#include <iterator>
#include <memory>
#include <span>
#include <string>
#include <string_view>
#include <vector>

namespace {

void writeWord(std::vector<std::uint8_t> &bytes, std::size_t offset, std::uint32_t value) {
  for (unsigned byte = 0; byte < 4; ++byte) {
    bytes[offset + byte] = static_cast<std::uint8_t>(value >> (byte * 8));
  }
}

bool require(bool condition, const char *message) {
  if (!condition) {
    std::fprintf(stderr, "%s\n", message);
  }
  return condition;
}

std::string sha256(std::span<const std::uint8_t> bytes) {
  return lucent::content::sha256_hex(
      lucent::content::sha256({reinterpret_cast<const std::byte *>(bytes.data()), bytes.size()}));
}

std::vector<std::uint8_t> residentFixture() {
  std::vector<std::uint8_t> bytes(0x800u + vagrant::kResidentHeader.textBytes, 0u);
  constexpr std::array<std::uint8_t, 8> magic{'P', 'S', '-', 'X', ' ', 'E', 'X', 'E'};
  std::copy(magic.begin(), magic.end(), bytes.begin());
  writeWord(bytes, 0x10u, vagrant::kResidentHeader.entry);
  writeWord(bytes, 0x14u, vagrant::kResidentHeader.globalPointer);
  writeWord(bytes, 0x18u, vagrant::kResidentHeader.textAddress);
  writeWord(bytes, 0x1Cu, vagrant::kResidentHeader.textBytes);
  writeWord(bytes, 0x30u, vagrant::kResidentHeader.stackBase);
  writeWord(bytes, 0x34u, vagrant::kResidentHeader.stackOffset);
  const auto callOffset = 0x800u + vagrant::resident::kTitleCallSite - vagrant::kResidentHeader.textAddress;
  writeWord(bytes, callOffset, 0x0C01C4CDu); // exact retail JAL word, independent of the entry gate
  writeWord(bytes, callOffset + 4u, vagrant::resident::kTitleCallDelayWord);
  writeWord(bytes, callOffset + 8u, 0x0000000Du); // stop the synthetic resident continuation
  return bytes;
}

std::vector<std::uint8_t> titleFixture() {
  const auto entryOffset = vagrant::resident::kTitleEntry - vagrant::resident::kTitleOverlayBase;
  std::vector<std::uint8_t> bytes(entryOffset + 12u, 0u);
  writeWord(bytes, entryOffset, 0x24020007u);      // addiu v0, zero, 7
  writeWord(bytes, entryOffset + 4u, 0x03E00008u); // jr ra
  return bytes;
}

std::vector<std::uint8_t> readFile(const std::filesystem::path &path) {
  std::ifstream stream(path, std::ios::binary);
  return {std::istreambuf_iterator<char>(stream), std::istreambuf_iterator<char>()};
}

bool syntheticCall() {
  const auto residentBytes = residentFixture();
  const auto titleBytes = titleFixture();
  const std::vector<std::uint8_t> battleBytes(4u, 0u);
  const std::vector<std::uint8_t> initBytes(4u, 0u);
  const std::array<vagrant::OverlaySpec, 3> specs{{
      {vagrant::OverlayKind::Title,
       "TITLE.PRG",
       vagrant::resident::kTitleOverlayBase,
       titleBytes.size(),
       sha256(titleBytes)},
      {vagrant::OverlayKind::Battle,
       "BATTLE.PRG",
       vagrant::resident::kTitleOverlayBase,
       battleBytes.size(),
       sha256(battleBytes)},
      {vagrant::OverlayKind::InitBattle, "INITBTL.PRG", 0x800F9800u, initBytes.size(), sha256(initBytes)},
  }};
  vagrant::VagrantRuntime runtime;
  psxport_install_game(runtime);
  auto game = std::make_unique<Game>();
  Core &core = game->core;
  const auto resident = runtime.loadResidentImage(core, residentBytes, "SLUS_010.40");
  vagrant::OverlayImages overlays(core, specs);
  const auto title = overlays.load(vagrant::OverlayKind::Title, titleBytes);
  if (!resident.identity.has_value() || !title.identity.has_value()) {
    return require(false, "synthetic images were refused");
  }
  core.pc = vagrant::resident::kTitleCallSite;
  core.r[2] = 0xAAu;
  const auto callsBefore = core.lightrecExecutor().counters().calls;
  const auto budget = psx::cpu::ExecutionBudget::fromCycles(200u);
  const auto reject = [&](psx::cpu::ImageIdentity residentImage, psx::cpu::ImageIdentity titleImage) {
    const auto result = vagrant::enterTitle(core, residentImage, titleImage, budget);
    return require(result.reason == psx::cpu::ExecutionExitReason::Fault && !result.detail.empty(),
                   "invalid TITLE transition was admitted") &&
           require(core.lightrecExecutor().counters().calls == callsBefore,
                   "refused TITLE transition entered the executor") &&
           require(core.r[2] == 0xAAu, "refused TITLE transition changed guest result");
  };
  if (!reject({}, *title.identity) || !reject(*resident.identity, {})) {
    return false;
  }
  core.pc -= 4u;
  if (!reject(*resident.identity, *title.identity)) {
    return false;
  }
  core.pc = vagrant::resident::kTitleCallSite;
  const auto call = core.mem_r32(core.pc);
  core.mem_w32(core.pc, 0u);
  if (!reject(*resident.identity, *title.identity)) {
    return false;
  }
  core.mem_w32(core.pc, call);
  core.mem_w32(core.pc + 4u, 0x24020001u);
  if (!reject(*resident.identity, *title.identity)) {
    return false;
  }
  core.mem_w32(core.pc + 4u, vagrant::resident::kTitleCallDelayWord);
  const auto result = vagrant::enterTitle(core, *resident.identity, *title.identity, budget);
  if (!require(result.reason == psx::cpu::ExecutionExitReason::HostService,
               "resident JAL did not return to synthetic stop") ||
      !require(result.guestPc == vagrant::resident::kTitleCallSite + 12u, "wrong resident continuation") ||
      !require(core.r[31] == vagrant::resident::kTitleCallSite + 8u, "JAL did not set the retail return address") ||
      !require(core.r[2] == 7u, "TITLE entry did not execute") ||
      !require(core.lightrecExecutor().counters().executedBlocks > 0u, "no translated block executed") ||
      !require(core.lightrecExecutor().counters().fallback.calls == 0u, "TITLE call interpreted a block")) {
    return false;
  }
  const auto battle = overlays.load(vagrant::OverlayKind::Battle, battleBytes);
  if (!require(static_cast<bool>(battle), "BATTLE replacement was refused")) {
    return false;
  }
  core.pc = vagrant::resident::kTitleCallSite;
  core.r[2] = 0xAAu;
  const auto postCalls = core.lightrecExecutor().counters().calls;
  const auto stale = vagrant::enterTitle(core, *resident.identity, *title.identity, budget);
  return require(stale.reason == psx::cpu::ExecutionExitReason::Fault, "retired TITLE generation was admitted") &&
         require(core.lightrecExecutor().counters().calls == postCalls,
                 "retired TITLE generation entered the executor") &&
         require(core.r[2] == 0xAAu, "retired TITLE generation changed guest result");
}

bool retailAdmission(const std::filesystem::path &directory) {
  const auto residentBytes = readFile(directory / "SLUS_010.40");
  const auto titleBytes = readFile(directory / "TITLE.PRG");
  if (!require(!residentBytes.empty() && !titleBytes.empty(), "exact retail inputs are missing")) {
    return false;
  }
  vagrant::VagrantRuntime runtime;
  psxport_install_game(runtime);
  auto game = std::make_unique<Game>();
  Core &core = game->core;
  const auto resident = runtime.loadResidentImage(core, residentBytes, "SLUS_010.40");
  vagrant::OverlayImages overlays(core);
  const auto title = overlays.load(vagrant::OverlayKind::Title, titleBytes);
  if (!resident.identity.has_value() || !title.identity.has_value()) {
    return require(false, "retail image admission failed");
  }
  core.pc = vagrant::resident::kTitleCallSite;
  if (!require(vagrant::validateTitleEntry(core, *resident.identity, *title.identity).empty(),
               "retail TITLE transition was refused")) {
    return false;
  }
  core.mem_w32(core.pc, 0u);
  const bool alteredRefused = !vagrant::validateTitleEntry(core, *resident.identity, *title.identity).empty();
  if (!require(alteredRefused, "altered retail call was admitted")) {
    return false;
  }
  std::printf("retail TITLE entry admission: 1/1 exact accepted; changed call 1/1 refused\n");
  return true;
}

} // namespace

int main(int argc, char **argv) {
  if (!syntheticCall()) {
    return 1;
  }
  if (argc == 3 && std::string_view(argv[1]) == "--retail-input-dir") {
    return retailAdmission(argv[2]) ? 0 : 1;
  }
  return require(argc == 1, "usage: vagrant_title_entry [--retail-input-dir DIRECTORY]") ? 0 : 2;
}
