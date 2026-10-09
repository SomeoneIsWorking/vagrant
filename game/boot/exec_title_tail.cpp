#include "boot/exec_title_tail.h"

#include "boot/resident_facts.h"
#include "core.h"

#include <cstdlib>
#include <lucent/log.h>

namespace vagrant {

ExecTitleTail::ExecTitleTail() = default;

ExecTitleTail::ExecTitleTail(std::unique_ptr<dynarec::GuestContinuation> continuation)
    : phase_(std::move(continuation)) {
}

void ExecTitleTail::begin(Core &core, std::uint32_t startState) {
  if (state_ != ExecTitleTailState::Cold) {
    lucent::error("vagrant-exec-tail", "vs_main_execTitle tail began more than once");
    std::abort();
  }
  // The prologue's frame, so the guest epilogue restores the caller's s0 and returns into vs_main_exec.
  core.r[29] -= resident::kExecTitleFrameSize;
  const std::uint32_t frame = core.r[29];
  core.mem_w32(frame + resident::kExecTitleSavedS0, core.r[16]);
  core.mem_w32(frame + resident::kExecTitleSavedRa, resident::kExecTitleReturn);
  core.r[16] = resident::kExecTitleStackSlot;
  core.r[2] = startState;

  phase_.begin(core, "vs_main_execTitle tail", resident::kExecTitleTail, resident::kExecTitleReturn);
  state_ = ExecTitleTailState::Running;
  advanceAfterField(core);
}

void ExecTitleTail::advanceAfterField(Core &core) {
  if (state_ != ExecTitleTailState::Running) {
    return;
  }
  const dynarec::ContinuationStep step = phase_.advance();
  if (step.kind == dynarec::ContinuationStep::Kind::Suspended) {
    lucent::debug(
        "vagrant-exec-tail", "suspended at 0x{:08X} ra=0x{:08X} sp=0x{:08X}", step.pc, core.r[31], core.r[29]);
    return;
  }
  state_ = ExecTitleTailState::Complete;
  lucent::info("vagrant-exec-tail", "vs_main_execTitle returned {}", step.value);
}

} // namespace vagrant
