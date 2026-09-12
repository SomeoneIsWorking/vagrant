#include "core.h"
#include "vagrant_runtime.h"

#include <algorithm>
#include <array>
#include <cstdint>
#include <cstdio>
#include <span>
#include <vector>

namespace {

void writeWord(std::vector<std::uint8_t> &bytes, std::size_t offset, std::uint32_t value) {
  for (unsigned byte = 0; byte < 4; ++byte) {
    bytes[offset + byte] = static_cast<std::uint8_t>(value >> (byte * 8));
  }
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
  writeWord(bytes, 0x800u, 0x03E00008u);
  return bytes;
}

bool require(bool condition, const char *message) {
  if (!condition) {
    std::fprintf(stderr, "%s\n", message);
  }
  return condition;
}

} // namespace

int main() {
  vagrant::VagrantRuntime runtime;
  psxport_install_game(runtime);
  Core core;
  if (!require(core.gameCtx != nullptr, "VagrantRuntime did not create its per-Core title context")) {
    return 1;
  }
  const auto image = residentFixture();
  const auto loaded = runtime.loadResidentImage(core, image, "SLUS_010.40");
  if (!require(static_cast<bool>(loaded), "measured resident image was refused") ||
      !require(core.pc == vagrant::kResidentHeader.entry, "resident entry was not published") ||
      !require(core.currentImageIdentity(vagrant::kResidentHeader.entry).has_value(),
               "resident image was not registered in the framework catalog")) {
    return 1;
  }

  auto wrongHeader = image;
  writeWord(wrongHeader, 0x10u, vagrant::kResidentHeader.entry + 4u);
  const auto refused = runtime.loadResidentImage(core, wrongHeader, "SLUS_010.40");
  return require(!refused, "different PS-X header was accepted as Vagrant Story") ? 0 : 1;
}
