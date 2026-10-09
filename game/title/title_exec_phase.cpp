#include "title/title_exec_phase.h"

#include "core.h"
#include "runtime/vagrant_context.h"
#include "title/title_exec_facts.h"

#include <cstdlib>
#include <lucent/log.h>

namespace vagrant {

TitleExecPhase::TitleExecPhase() = default;

TitleExecPhase::TitleExecPhase(std::unique_ptr<dynarec::GuestContinuation> continuation)
    : phase_(std::move(continuation)) {
}

void TitleExecPhase::begin(Core &core, std::uint32_t menuItem) {
  if (state_ != TitleExecState::Cold) {
    lucent::error("vagrant-title-exec", "TITLE exec began more than once");
    std::abort();
  }
  // The prologue's frame, so the guest epilogue restores the registers it would have saved.
  core.r[29] -= title_exec::kFrameSize;
  const std::uint32_t frame = core.r[29];
  core.mem_w32(frame + title_exec::kSavedRa, title_exec::kReturn);
  core.mem_w32(frame + title_exec::kSavedFp, core.r[30]);
  for (std::uint32_t index = 0u; index < 8u; ++index) {
    core.mem_w32(frame + title_exec::kSavedS0 + index * 4u, core.r[16u + index]);
  }
  core.r[18] = menuItem;
  core.r[23] = 1u;
  core.r[30] = title_exec::kDataBase;

  phase_.begin(core, "TITLE vs_title_exec", title_exec::kLoopTop, title_exec::kReturn);
  state_ = TitleExecState::Running;
  advanceAfterField(core);
}

void TitleExecPhase::advanceAfterField(Core &core) {
  if (state_ != TitleExecState::Running) {
    return;
  }
  const dynarec::ContinuationStep step = phase_.advance();
  if (step.kind == dynarec::ContinuationStep::Kind::Suspended) {
    lucent::debug("vagrant-title-exec", "suspended at 0x{:08X}", step.pc);
    // The guest's VSync ends the pass it drew since the last one; the menu's DrawPrim queue is flushed there.
    if (step.frameBoundary) {
      contextOf(core).titleMenu.frameCompleted();
    }
    return;
  }
  selectedOption_ = step.value;
  state_ = TitleExecState::Complete;
  lucent::info("vagrant-title-exec", "TITLE vs_title_exec returned option {}", selectedOption_);
}

} // namespace vagrant
