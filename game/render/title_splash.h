#pragma once

#include "core/resident_phase.h"

#include <cstdint>

class Core;

namespace vagrant {

enum class TitleSplashState {
  Cold,
  InitialFieldWait,
  PublisherFieldWait,
  DeveloperFieldWait,
  Complete,
};

// Finite host owner for TITLE's publisher/developer splash. The original 0xB0-byte guest frame stays
// live through runtime guest execution, and each retail VSync becomes one return to the frame owner.
class TitleSplashPhase {
public:
  TitleSplashPhase();
  explicit TitleSplashPhase(ResidentCallServices services);

  void begin(Core &core);
  void advanceAfterField(Core &core);

  TitleSplashState state() const {
    return state_;
  }
  bool complete() const {
    return state_ == TitleSplashState::Complete;
  }

private:
  void beginPublisherField(Core &core);
  void beginDeveloperField(Core &core);
  void finishEnvironment(Core &core);
  void setDisplayEnvironments(Core &core, std::uint32_t index);

  ResidentCallServices services_;
  TitleSplashState state_ = TitleSplashState::Cold;
  std::uint32_t fieldIndex_ = 0u;
  std::uint8_t monoSound_ = 0u;
  std::uint8_t vibrationOn_ = 0u;
};

} // namespace vagrant
