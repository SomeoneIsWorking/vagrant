#include "core/resident_phase.h"

#include "cd/cd_facts.h"
#include "cd/native_file.h"
#include "core.h"
#include "core/game_time.h"
#include "core/resident_facts.h"
#include "guest_call.h"
#include "render/title_splash_facts.h"
#include "vagrant_context.h"

#include <cstdlib>
#include <lucent/log.h>

namespace {

std::uint32_t call0(Core &core, std::uint32_t address) {
  rc0(&core, address);
  return core.r[2];
}

std::uint32_t call1(Core &core, std::uint32_t address, std::uint32_t a0) {
  rc1(&core, address, a0);
  return core.r[2];
}

std::uint32_t call2(Core &core, std::uint32_t address, std::uint32_t a0, std::uint32_t a1) {
  rc2(&core, address, a0, a1);
  return core.r[2];
}

std::uint32_t
call4(Core &core, std::uint32_t address, std::uint32_t a0, std::uint32_t a1, std::uint32_t a2, std::uint32_t a3) {
  rc4(&core, address, a0, a1, a2, a3);
  return core.r[2];
}

void writeRect(Core &core, std::uint32_t address, std::int16_t x, std::int16_t y, std::int16_t w, std::int16_t h) {
  core.mem_w16(address, static_cast<std::uint16_t>(x));
  core.mem_w16(address + 2u, static_cast<std::uint16_t>(y));
  core.mem_w16(address + 4u, static_cast<std::uint16_t>(w));
  core.mem_w16(address + 6u, static_cast<std::uint16_t>(h));
}

} // namespace

namespace vagrant {

ResidentCallServices productionResidentCallServices() {
  return {.call0 = call0, .call1 = call1, .call2 = call2, .call4 = call4, .readFile = cd::readNativeFile};
}

ResidentPhase::ResidentPhase() : ResidentPhase(productionResidentCallServices()) {}

ResidentPhase::ResidentPhase(ResidentCallServices services) : services_(services) {
  requireServices(services_);
}

void ResidentPhase::requireServices(const ResidentCallServices &services) {
  if (services.call0 && services.call1 && services.call2 && services.call4 && services.readFile) {
    return;
  }
  lucent::error("vagrant-resident", "ResidentPhase requires every finite guest-call service");
  std::abort();
}

void ResidentPhase::begin(Core &core) {
  if (state_ != ResidentPhaseState::Cold) {
    lucent::error("vagrant-resident", "resident bootstrap began more than once");
    std::abort();
  }

  services_.call0(core, resident::kCxxMain);

  // _sysInit's 0x20-byte frame remains live while InitCARD waits for one display field. The nested
  // 0x20-byte InitCARD frame is retained as well, so any field service sees the same guest stack
  // depth as retail. The VSync at 0x8002E950 itself is deliberately not called.
  core.r[29] -= 0x20u;
  services_.call1(core, resident::kSetVideoMode, 0u);
  services_.call1(core, resident::kSetDispMask, 0u);
  services_.call0(core, resident::kResetCallback);
  services_.call1(core, resident::kResetGraph, 0u);
  services_.call1(core, resident::kSetGraphDebug, 0u);
  core.r[29] -= 0x20u;
  services_.call1(core, resident::kCardStop, 0u);
  state_ = ResidentPhaseState::InitCardFieldWait;
}

void ResidentPhase::finishInitCard(Core &core) {
  const std::uint32_t cardWasStarted = services_.call0(core, resident::kCardStart);
  const std::uint32_t cardProbe = services_.call0(core, resident::kCardProbe);
  // InitCARD's original a0 is zero. Its probe only decides whether to force that saved argument to
  // zero, so both retail branches pass zero for this exact call site.
  services_.call1(core, resident::kCardConfigure, 0u);
  services_.call0(core, resident::kCardConfigureEvents);
  services_.call0(core, resident::kCardConfigureHardware);
  services_.call0(core, resident::kCardConfigureSoftware);
  services_.call0(core, resident::kCardConfigureFilesystem);
  if (cardWasStarted == 1u) {
    services_.call0(core, resident::kCardResume);
  }
  (void)cardProbe;
  core.r[29] += 0x20u;

  // StartCARD has its own 0x18-byte frame. Its initial status decides the final resume call.
  core.r[29] -= 0x18u;
  const std::uint32_t startWasActive = services_.call0(core, resident::kCardStart);
  services_.call0(core, resident::kCardStartCom);
  services_.call1(core, resident::kCardStop, 0u);
  if (startWasActive == 1u) {
    services_.call0(core, resident::kCardResume);
  }
  core.r[29] += 0x18u;
}

void ResidentPhase::finishSysInit(Core &core) {
  services_.call0(core, resident::kBuInit);
  services_.call2(core, resident::kPadInitDirect, resident::kPadBuffer0, resident::kPadBuffer1);
  services_.call2(core, resident::kPadResetDefaults, 0u, resident::kPadBuffer0);
  services_.call2(core, resident::kPadResetDefaults, 0x10u, resident::kPadBuffer1);
  services_.call0(core, resident::kPadStartCom);
  services_.call0(core, resident::kUnlockPadModeSwitch);
  services_.call0(core, resident::kResetPadAct);
  services_.call0(core, resident::kReverbOff);
  services_.call0(core, resident::kDsInit);
  static_cast<VagrantContext *>(core.gameCtx)->libDsField.completeSynchronousInit(core);
  services_.call0(core, resident::kInitRand);
  core.mem_w32(resident::kResetEnabled, 1u);
  core.mem_w32(resident::kSaveGameClearData, 0u);
  core.r[29] += 0x20u;

  services_.call1(core, resident::kOverlayGetSp, resident::kTitleOuterStack);
}

void ResidentPhase::beginTitleReinit(Core &core) {
  // Keep _sysReinit's 0x30-byte frame live at the next asynchronous boundary. rect2 is the full VRAM
  // clear exactly materialised at sp+0x20 by retail.
  core.r[29] -= 0x30u;
  const std::uint32_t clearRect = core.r[29] + 0x20u;
  writeRect(core, clearRect, 0, 0, 1024, 512);
  services_.call0(core, resident::kResetCallback);
  services_.call1(core, resident::kResetGraph, 1u);
  services_.call1(core, resident::kSetGraphDebug, 0u);
  services_.call4(core, resident::kClearImage, clearRect, 0u, 0u, 0u);
  services_.call1(core, resident::kDrawSync, 0u);

  // _displayLoadingScreen's 0x38-byte frame remains live for VSync(2). Its two stack arguments to
  // _initScreen are explicitly zero in the executable and the local RECT is sp+0x18.
  core.r[29] -= 0x38u;
  core.mem_w32(core.r[29] + 0x10u, 0u);
  core.mem_w32(core.r[29] + 0x14u, 0u);
  services_.call4(core, resident::kInitScreen, 0x140u, 0xF0u, core.mem_r32(resident::kProjectionDistance), 0u);
  const std::uint32_t loadingRect = core.r[29] + 0x18u;
  writeRect(core, loadingRect, 0, 0, 1024, 512);
  services_.call4(core, resident::kClearImage2, loadingRect, 0u, 0u, 0u);
  services_.call1(core, resident::kDrawSync, 0u);

  loadingFieldsRemaining_ = 2u;
  state_ = ResidentPhaseState::LoadingScreenFieldWait;
}

void ResidentPhase::finishLoadingScreen(Core &core) {
  const std::uint32_t loadingRect = core.r[29] + 0x18u;
  const std::int32_t width = static_cast<std::int32_t>(core.mem_r8(resident::kLoadingImageHeader)) |
                             (static_cast<std::int32_t>(core.mem_r8(resident::kLoadingImageHeader + 1u)) << 8);
  const std::int32_t height = static_cast<std::int32_t>(core.mem_r8(resident::kLoadingImageHeader + 2u)) |
                              (static_cast<std::int32_t>(core.mem_r8(resident::kLoadingImageHeader + 3u)) << 8);
  const std::int16_t centeredX = static_cast<std::int16_t>((320 - width) / 2);
  const std::int16_t centeredY = static_cast<std::int16_t>((224 - height) / 2);

  writeRect(
      core, loadingRect, centeredX, centeredY, static_cast<std::int16_t>(width), static_cast<std::int16_t>(height));
  services_.call2(core, resident::kLoadImage, loadingRect, resident::kLoadingImageData);
  writeRect(core,
            loadingRect,
            static_cast<std::int16_t>(centeredX + 320),
            centeredY,
            static_cast<std::int16_t>(width),
            static_cast<std::int16_t>(height));
  services_.call2(core, resident::kLoadImage, loadingRect, resident::kLoadingImageData);
  services_.call1(core, resident::kDrawSync, 0u);
  services_.call1(core, resident::kSetDispMask, 1u);
  core.r[29] += 0x38u;
}

void ResidentPhase::beginMenuSound(Core &core) {
  services_.call0(core, resident::kReverbOn);
  services_.call0(core, resident::kInitGeom);
  services_.call1(core, resident::kDrawSyncCallback, resident::kGpuSyncCallback);
  services_.call1(core, resident::kVSyncCallback, resident::kVSyncVoidCallback);
  services_.call2(core, resident::kInitHeap, resident::kHeapBase, resident::kHeapSize);
  services_.call0(core, resident::kInitCdQueue);

  // _diskReset's blocking DsControlB calls are already native synchronous commands. Its final
  // VSync(3) is not: preserve those three complete fields explicitly, with the original 0x18-byte
  // frame live, then enter _loadMenuSound on the post-field boundary.
  core.r[29] -= 0x18u;
  services_.call2(core, cd::kDsControlB, 9u, 0u);
  services_.call0(core, cd::kDsFlush);
  core.mem_w8(cd::kDiskState + 1u, 0x80u);
  core.mem_w8(cd::kDiskState + 28u, 0x80u);
  core.mem_w8(cd::kDiskState + 2u, 0u);
  core.mem_w8(cd::kDiskState, 0u);
  core.mem_w32(cd::kDiskState + 44u, 0u);
  core.mem_w32(cd::kCdReadBuffer, 0u);
  services_.call2(core, cd::kDsControlB, 0x0Eu, cd::kDsControlBuffer);
  diskResetFieldsRemaining_ = 3u;
  state_ = ResidentPhaseState::DiskResetFieldWait;
}

void ResidentPhase::beginMenuSoundBody(Core &core) {
  // Keep _loadMenuSound's 0x18-byte frame live across its four blocking file reads. Each retail
  // diskLoadFile loop performs VSync(0), then gametimeUpdate processes the CD queue. The host field
  // is now the wait; advanceMenuLoad performs only the finite post-field half.
  core.r[29] -= 0x18u;
  services_.call0(core, resident::kInitSound);
  services_.call1(core, resident::kSetCdVolume, 0x7Fu);
  menuLoadIndex_ = 0u;
  beginMenuLoad(core);
}

void ResidentPhase::beginMenuLoad(Core &core) {
  struct MenuLoad {
    std::uint32_t lba;
    std::uint32_t size;
    bool heapBuffer;
  };
  static constexpr MenuLoad kLoads[] = {
      {resident::kWave0000Lba, resident::kWave0000Size, true},
      {resident::kWave0005Lba, resident::kWave0005Size, true},
      {resident::kWave0200Lba, resident::kWave0200Size, true},
      {resident::kEffect00Lba, resident::kEffect00Size, false},
  };

  const MenuLoad &load = kLoads[menuLoadIndex_];
  menuLoadBuffer_ = load.heapBuffer ? services_.call1(core, resident::kAllocHeapR, load.size) : resident::kSfxData;
  if (!services_.readFile(core, load.lba, load.size, menuLoadBuffer_)) {
    lucent::error("vagrant-resident",
                  "menu file read failed at LBA {} size {} destination 0x{:08X}",
                  load.lba,
                  load.size,
                  menuLoadBuffer_);
    std::abort();
  }
  state_ = ResidentPhaseState::MenuSoundLoadFieldWait;
}

void ResidentPhase::advanceMenuLoad(Core &core) {
  game_time::advance(core);
  finishMenuLoad(core);
}

void ResidentPhase::finishMenuLoad(Core &core) {
  if (menuLoadIndex_ < 2u) {
    services_.call2(core, resident::kLoadWaveBank, menuLoadBuffer_, 1u);
    services_.call1(core, resident::kFreeHeapR, menuLoadBuffer_);
  } else if (menuLoadIndex_ == 2u) {
    services_.call4(core, resident::kLoadProgramBank, menuLoadBuffer_, 0u, 1u, 0u);
    services_.call1(core, resident::kFreeHeapR, menuLoadBuffer_);
  } else {
    services_.call1(core, resident::kBindSfxBlob, menuLoadBuffer_);
  }

  if (++menuLoadIndex_ < 4u) {
    beginMenuLoad(core);
    return;
  }

  core.mem_w32(resident::kSoundControl0, 1u);
  core.mem_w32(resident::kSoundControl1, 2u);
  core.mem_w32(resident::kSoundControl2, 0x80u);
  core.mem_w32(resident::kSoundControl3, 0x200u);
  core.mem_w32(resident::kSoundControl4, 0x1000u);
  core.mem_w32(resident::kSoundControl5, 0x100000u);
  core.r[29] += 0x18u;
  finishTitleReinit(core);
}

void ResidentPhase::finishTitleReinit(Core &core) {
  services_.call0(core, resident::kResetPadAct);
  core.mem_w32(resident::kInGame, 0u);
  services_.call0(core, resident::kUnlockPadModeSwitch);
  for (std::uint32_t index = 0; index < 32u; ++index) {
    core.mem_w32(resident::kButtonHeldFrameCount + index * 4u, 0u);
  }
  core.mem_w32(resident::kGameTime, 0u);
  core.mem_w32(resident::kMainStateFlag, 0u);
  core.r[29] += 0x30u;
  if (!services_.readFile(core, resident::kTitlePrgLba, resident::kTitlePrgSize, resident::kTitleOverlayBase)) {
    lucent::error("vagrant-resident",
                  "TITLE.PRG read failed at LBA {} size {} destination 0x{:08X}",
                  resident::kTitlePrgLba,
                  resident::kTitlePrgSize,
                  resident::kTitleOverlayBase);
    std::abort();
  }
  state_ = ResidentPhaseState::TitleProgramLoadFieldWait;
  lucent::info("vagrant-resident", "finite TITLE reinitialisation loaded TITLE.PRG; entry follows one host field");
}

void ResidentPhase::enterTitleProgram(Core &core) {
  state_ = ResidentPhaseState::TitleProgramRunning;
  if (core.mem_r32(resident::kSaveGameClearData) != 0u) {
    core.mem_w32(resident::kSaveGameClearData, 0u);
    core.mem_w32(title_splash::kTitleScreenCount, 0u);
    services_.call0(core, title_splash::kGameSaveScreen);
  }
  services_.call0(core, title_splash::kInitGameData);
  static_cast<VagrantContext *>(core.gameCtx)->titleSplash.begin(core);
  state_ = ResidentPhaseState::TitleSplashRunning;
  lucent::info("vagrant-resident", "TITLE entry prefix reached the native-owned publisher/developer splash");
}

void ResidentPhase::advanceAfterField(Core &core) {
  if (state_ == ResidentPhaseState::TitleProgramLoadFieldWait) {
    enterTitleProgram(core);
    return;
  }
  if (state_ == ResidentPhaseState::TitleSplashRunning) {
    if (!static_cast<VagrantContext *>(core.gameCtx)->titleSplash.complete()) {
      return;
    }
    core.mem_w32(title_splash::kIntroMoviePlaying, 0u);
    core.mem_w32(title_splash::kTitleScreenCount, core.mem_r32(title_splash::kTitleScreenCount) + 1u);
    static_cast<VagrantContext *>(core.gameCtx)->titleSaveCheck.begin(core);
    state_ = ResidentPhaseState::TitleSaveCheckRunning;
    return;
  }
  if (state_ == ResidentPhaseState::TitleSaveCheckRunning) {
    auto &saveCheck = static_cast<VagrantContext *>(core.gameCtx)->titleSaveCheck;
    saveCheck.advanceAfterField(core);
    if (!saveCheck.complete()) {
      return;
    }
    for (std::uint32_t index = 0u; index < 8u; ++index) {
      core.mem_w8(title_splash::kMenuItemStates + index * 8u, 0u);
    }
    services_.call0(core, title_splash::kCopyTitleBgData);
    state_ = ResidentPhaseState::TitleIntroBoundary;
    lucent::info("vagrant-resident", "TITLE save-file check completed; next owner is _initIntroMovie");
    return;
  }
  if (state_ == ResidentPhaseState::InitCardFieldWait) {
    finishInitCard(core);
    finishSysInit(core);
    beginTitleReinit(core);
    return;
  }
  if (state_ != ResidentPhaseState::LoadingScreenFieldWait) {
    if (state_ == ResidentPhaseState::DiskResetFieldWait) {
      if (--diskResetFieldsRemaining_ == 0u) {
        core.r[29] += 0x18u;
        beginMenuSoundBody(core);
      }
      return;
    }
    if (state_ == ResidentPhaseState::MenuSoundLoadFieldWait) {
      advanceMenuLoad(core);
    }
    return;
  }
  if (--loadingFieldsRemaining_ != 0u) {
    return;
  }
  finishLoadingScreen(core);
  beginMenuSound(core);
}

} // namespace vagrant
