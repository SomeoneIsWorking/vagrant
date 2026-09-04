#include "core/player_cli.h"

#include <cstdio>

int main() {
  char program[] = "vagrant_port";
  char help[] = "--help";
  char shortHelp[] = "-h";
  char image[] = "owned/SLUS_010.40";
  char extra[] = "extra";

  char *longHelpArgs[] = {program, help};
  char *shortHelpArgs[] = {program, shortHelp};
  char *runArgs[] = {program, image};
  char *errorArgs[] = {program, image, extra};
  if (parsePlayerCli(2, longHelpArgs).action != PlayerCliAction::Help ||
      parsePlayerCli(2, shortHelpArgs).action != PlayerCliAction::Help) {
    std::fprintf(stderr, "player CLI did not recognize both help spellings\n");
    return 1;
  }
  const PlayerCliOptions run = parsePlayerCli(2, runArgs);
  if (run.action != PlayerCliAction::Run || run.executablePath != image) {
    std::fprintf(stderr, "player CLI displaced the explicit executable route\n");
    return 1;
  }
  if (parsePlayerCli(1, longHelpArgs).action != PlayerCliAction::Run ||
      parsePlayerCli(3, errorArgs).action != PlayerCliAction::Error) {
    std::fprintf(stderr, "player CLI default/error contract drifted\n");
    return 1;
  }
  printPlayerUsage();
  return 0;
}
