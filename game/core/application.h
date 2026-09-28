#pragma once

#include "psx_exe_image.h"

#include <cstdint>
#include <memory>
#include <string>

class Game;

namespace vagrant {

// The process composition owner: it is the only place that knows the ORDER in which the machine
// becomes a Vagrant Story product.
//
//   Game construction (which installs the title's per-Core products through GameRuntime)
//     -> the measured resident image is admitted and published
//     -> image-scoped native leaves are registered against that generation
//     -> the framework's platform sync boundary is preflighted
//     -> the title's measured boot phase runs
//     -> one finite field per display frame
//     -> the run-end census, with every denominator
//
// It composes; it does not implement. The per-Core products live in VagrantContext, the leaves in
// native_owners.h, the dispatch surface in dynarec_dispatch.h, and the boot/field behaviour in the
// owners the context already collects.
class Application {
public:
  Application();

  // Construct the machine and publish the authenticated resident image. Returns false with a named
  // reason; on failure no guest state has been modified and no override is installed.
  bool start(Game &game, const std::string &residentImagePath);

  // The measured resident bootstrap, then the bounded product loop. This call does not return while
  // the product is running.
  void run(Game &game);

  // The run-end census. Every number is paired with the denominator that makes it readable, and the
  // line states which framework-owned counters are read from the executor rather than counted here.
  // Takes a non-const `Game` because reading the framework's executor and per-Core owners is a
  // non-const reading in psxport; nothing here mutates the machine.
  void reportRunEnd(Game &game) const;
  [[nodiscard]] psx::cpu::ImageIdentity residentImage() const {
    return residentImage_;
  }

private:
  psx::cpu::ImageIdentity residentImage_{};
  bool started_ = false;
};

// The product entry point. Owns the arguments' interpretation and the process return code, and
// composes `Application`; it holds no title state of its own.
int runApplication(int argc, char **argv);

} // namespace vagrant
