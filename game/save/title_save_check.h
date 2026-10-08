#pragma once

#include "boot/resident_phase.h"

#include <cstdint>

class Core;

namespace vagrant {

enum class TitleSaveCheckState {
  Cold,
  InitFieldWait,
  EventFieldWait,
  Complete,
};

// Owner for TITLE _saveFileExists 0x8006E988; each retail VSync(2) is one return to VagrantFrameDriver.
class TitleSaveCheck {
public:
  TitleSaveCheck();
  explicit TitleSaveCheck(ResidentCallServices services);

  void begin(Core &core);
  void advanceAfterField(Core &core);

  TitleSaveCheckState state() const {
    return state_;
  }
  bool complete() const {
    return state_ == TitleSaveCheckState::Complete;
  }
  bool saveFileExists() const {
    return saveFileExists_;
  }

private:
  void beginPort(Core &core, std::uint32_t port);
  void finish(Core &core, bool exists);
  void finishEventField(Core &core);
  void finishInitField(Core &core);

  ResidentCallServices services_;
  TitleSaveCheckState state_ = TitleSaveCheckState::Cold;
  std::uint32_t port_ = 0u;
  std::uint32_t eventState_ = 0u;
  bool saveFileExists_ = false;
};

} // namespace vagrant
