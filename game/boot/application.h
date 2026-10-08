#pragma once

#include "psx_exe_image.h"

#include <cstdint>
#include <memory>
#include <string>

class Game;

namespace vagrant {

// Process composition owner: the one place that knows the order the machine becomes a product.
class Application {
public:
  Application();

  // On failure no guest state is modified.
  bool start(Game &game, const std::string &residentImagePath);

  // Does not return while running.
  void run(Game &game);

  // Non-const Game because psxport's executor reads are non-const.
  void reportRunEnd(Game &game) const;
  [[nodiscard]] psx::cpu::ImageIdentity residentImage() const {
    return residentImage_;
  }

private:
  psx::cpu::ImageIdentity residentImage_{};
  bool started_ = false;
};

int runApplication(int argc, char **argv);

} // namespace vagrant
