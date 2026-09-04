#pragma once

enum class PlayerCliAction {
  Run,
  Help,
  Error,
};

struct PlayerCliOptions {
  PlayerCliAction action = PlayerCliAction::Run;
  const char *executablePath = nullptr;
};

PlayerCliOptions parsePlayerCli(int argc, char **argv);
void printPlayerUsage();
