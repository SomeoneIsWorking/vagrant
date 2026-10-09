#pragma once

#include "cd/native_file.h"

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
  TitleExecRunning,
  ExecTitleTailRunning,
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
  cd::ReadSector readSector = nullptr;
};

ResidentCallServices productionResidentCallServices();

// Calls finite guest leaves in retail order and turns each field wait into a host state; _diskReset and _loadMenuSound
// are state machines.
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
