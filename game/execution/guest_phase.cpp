#include "execution/guest_phase.h"

#include <cstdlib>
#include <lucent/log.h>

namespace vagrant::dynarec {

GuestPhase::GuestPhase() : GuestPhase(std::make_unique<ResumableContinuation>()) {
}

GuestPhase::GuestPhase(std::unique_ptr<GuestContinuation> continuation) : continuation_(std::move(continuation)) {
}

void GuestPhase::begin(Core &core, std::string_view owner, std::uint32_t entry, std::uint32_t returnPc) {
  owner_ = owner;
  continuation_->begin(core, entry, owner, returnPc);
}

ContinuationStep GuestPhase::advance() {
  ContinuationStep step = continuation_->advance();
  if (step.kind == ContinuationStep::Kind::Refused) {
    lucent::error("vagrant-phase", "{} stopped at 0x{:08X}: {}", owner_, step.pc, step.detail);
    std::abort();
  }
  return step;
}

} // namespace vagrant::dynarec
