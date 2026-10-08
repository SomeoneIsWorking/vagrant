#pragma once

#include "boot/resident_phase.h"

#include <cstdint>

class Core;

namespace vagrant {

enum class TitleMemcardInitState {
  Cold,
  FirstExtentReady,
  SecondExtentReady,
  EventSetupReady,
  Complete,
};

// Owner for TITLE `_initMemcard`; replaces the libds CD queue, whose interrupt completion cannot occur here.
class TitleMemcardInit {
public:
  TitleMemcardInit();
  explicit TitleMemcardInit(ResidentCallServices services);

  std::uint32_t invoke(Core &core, std::uint32_t init);

  TitleMemcardInitState state() const {
    return state_;
  }

private:
  void begin(Core &core);
  void finishFirstExtent(Core &core);
  void finishSecondExtent(Core &core);
  void setupEvents(Core &core);

  ResidentCallServices services_;
  TitleMemcardInitState state_ = TitleMemcardInitState::Cold;
};

} // namespace vagrant
