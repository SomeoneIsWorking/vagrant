#include "core/player_cli.h"

#include <cstdio>
#include <cstring>

PlayerCliOptions parsePlayerCli(int argc, char **argv) {
  if (argc == 2 && (std::strcmp(argv[1], "-h") == 0 || std::strcmp(argv[1], "--help") == 0)) {
    return {PlayerCliAction::Help, nullptr};
  }
  if (argc > 2) {
    return {PlayerCliAction::Error, nullptr};
  }
  return {PlayerCliAction::Run, argc == 2 ? argv[1] : nullptr};
}

void printPlayerUsage() {
  std::puts("Usage: vagrant_port [SLUS_010.40]\n"
            "Run the Vagrant Story (USA) native port. With no path, the player uses\n"
            "scratch/bin/vagrant/SLUS_010.40 and extracts it from the configured disc if needed.\n\n"
            "Options:\n"
            "  -h, --help  Show this help and exit");
}
