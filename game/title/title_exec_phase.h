#pragma once

#include "execution/guest_phase.h"

#include <cstdint>
#include <memory>

class Core;

namespace vagrant {

enum class TitleExecState {
  Cold,
  Running,
  Complete,
};

// The rest of TITLE `vs_title_exec` after `_saveFileExists`, run as guest code: each retail VSync suspends the call and
// the next field resumes it, so the intro movie, the Start-skip menu and the option loop are the game's own.
class TitleExecPhase {
public:
  TitleExecPhase();
  explicit TitleExecPhase(std::unique_ptr<dynarec::GuestContinuation> continuation);

  void begin(Core &core, std::uint32_t menuItem);
  void advanceAfterField(Core &core);

  TitleExecState state() const {
    return state_;
  }
  bool complete() const {
    return state_ == TitleExecState::Complete;
  }
  // The option `vs_title_exec` returned: 0 new game, 1 continue, 4 or 5 attract timeout.
  std::uint32_t selectedOption() const {
    return selectedOption_;
  }

private:
  dynarec::GuestPhase phase_;
  TitleExecState state_ = TitleExecState::Cold;
  std::uint32_t selectedOption_ = 0u;
};

} // namespace vagrant
