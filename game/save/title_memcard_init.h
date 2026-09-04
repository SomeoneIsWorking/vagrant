#pragma once

#include "core/resident_phase.h"

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

// Finite owner for TITLE `_initMemcard`. Each call preserves one retail polling boundary. Restricted
// file bytes still come from the user's disc; the native path replaces only the libds queue whose
// interrupt-driven completion cannot occur under psxport's synchronous controller.
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
