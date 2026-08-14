#include "cd/ds_control_contract.h"

#include <array>
#include <cstddef>
#include <cstdint>
#include <cstdio>

namespace {

struct UnsupportedCommand {
  uint8_t command;
  const char *classification;
};

// This is the contract expectation, not a second classifier: every value is
// fed through the exact helper included by ds_control.cpp.
constexpr std::array<uint8_t, 9> kExpectedOwnedCommands = {
    0x01, 0x02, 0x07, 0x08, 0x09, 0x0D, 0x0E, 0x15, 0x16,
};

constexpr std::array<UnsupportedCommand, 3> kUnsupportedCommands = {{
    {0x10, "query GetlocL"},
    {0x06, "read ReadN"},
    {0xFF, "unknown"},
}};

} // namespace

int main() {
  size_t accepted = 0;
  for (uint8_t command : kExpectedOwnedCommands) {
    if (!vagrant_cd::ownedControl(command)) {
      std::fprintf(stderr, "FAIL: allowed command 0x%02X was refused\n",
                   command);
      return 1;
    }
    ++accepted;
  }
  std::printf("allowed: %zu/%zu accepted\n", accepted,
              kExpectedOwnedCommands.size());

  size_t refused = 0;
  for (const UnsupportedCommand &command : kUnsupportedCommands) {
    if (vagrant_cd::ownedControl(command.command)) {
      std::fprintf(stderr, "FAIL: unsupported %s command 0x%02X was accepted\n",
                   command.classification, command.command);
      return 1;
    }
    ++refused;
  }
  std::printf("unsupported: %zu/%zu refused (query, read, unknown)\n", refused,
              kUnsupportedCommands.size());
  return 0;
}
