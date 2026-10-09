#pragma once

#include "execution/dynarec_dispatch.h"

#include <cstdint>
#include <memory>
#include <string_view>

class Core;

namespace vagrant::dynarec {

// One guest call that spans display fields, advanced once per host field. A refusal is fatal here, so a phase owner
// only sees a suspension or the returned value.
class GuestPhase {
public:
  GuestPhase();
  explicit GuestPhase(std::unique_ptr<GuestContinuation> continuation);

  void begin(Core &core, std::string_view owner, std::uint32_t entry, std::uint32_t returnPc);

  // Runs one field. `Suspended` carries whether the guest stopped at its own VSync; `Returned` carries `$v0`.
  ContinuationStep advance();

private:
  std::unique_ptr<GuestContinuation> continuation_;
  std::string owner_;
};

} // namespace vagrant::dynarec
