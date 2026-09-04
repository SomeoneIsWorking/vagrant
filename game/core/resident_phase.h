#pragma once

#include <cstdint>

class Core;

namespace vagrant {

enum class ResidentPhaseState {
  Cold,
  InitCardFieldWait,
  LoadingScreenFieldWait,
  DiskResetFieldWait,
  MenuSoundLoadFieldWait,
  TitleProgramLoadFieldWait,
  TitleProgramRunning,
  TitleSplashRunning,
  TitleSaveCheckRunning,
  TitleIntroBoundary,
  BattleProgramBoundary,
};

struct ResidentCallServices {
  using Call0 = std::uint32_t (*)(Core &, std::uint32_t);
  using Call1 = std::uint32_t (*)(Core &, std::uint32_t, std::uint32_t);
  using Call2 = std::uint32_t (*)(Core &, std::uint32_t, std::uint32_t, std::uint32_t);
  using Call4 = std::uint32_t (*)(Core &, std::uint32_t, std::uint32_t, std::uint32_t, std::uint32_t, std::uint32_t);
  using ReadFile = bool (*)(Core &, std::uint32_t, std::uint32_t, std::uint32_t);

  Call0 call0 = nullptr;
  Call1 call1 = nullptr;
  Call2 call2 = nullptr;
  Call4 call4 = nullptr;
  ReadFile readFile = nullptr;
};

ResidentCallServices productionResidentCallServices();

// Finite native owner for the resident bootstrap and the beginning of TITLE reinitialisation. It
// calls retained finite guest leaves in retail order, but turns every measured guest field wait
// through TITLE reinitialisation into explicit host-driver states. It owns _diskReset and
// _loadMenuSound as finite state machines without dispatching either VSync-driven routine whole.
class ResidentPhase {
public:
  ResidentPhase();
  explicit ResidentPhase(ResidentCallServices services);

  void begin(Core &core);
  void advanceAfterField(Core &core);

  ResidentPhaseState state() const {
    return state_;
  }
  std::uint32_t loadingFieldsRemaining() const {
    return loadingFieldsRemaining_;
  }

private:
  static void requireServices(const ResidentCallServices &services);
  void finishInitCard(Core &core);
  void finishSysInit(Core &core);
  void beginTitleReinit(Core &core);
  void finishLoadingScreen(Core &core);
  void beginMenuSound(Core &core);
  void beginMenuSoundBody(Core &core);
  void beginMenuLoad(Core &core);
  void advanceMenuLoad(Core &core);
  void finishMenuLoad(Core &core);
  void finishTitleReinit(Core &core);
  void enterTitleProgram(Core &core);

  ResidentCallServices services_;
  ResidentPhaseState state_ = ResidentPhaseState::Cold;
  std::uint32_t loadingFieldsRemaining_ = 0;
  std::uint32_t diskResetFieldsRemaining_ = 0;
  std::uint32_t menuLoadIndex_ = 0;
  std::uint32_t menuLoadBuffer_ = 0;
};

} // namespace vagrant
