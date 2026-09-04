#include "cd/cd_facts.h"
#include "core.h"
#include "core/resident_facts.h"
#include "core/resident_phase.h"
#include "game.h"
#include "render/title_splash_facts.h"
#include "save/title_memcard_facts.h"
#include "save/title_memcard_init.h"
#include "save/title_save_facts.h"
#include "sync/frame_loop.h"
#include "sync/vsync_facts.h"
#include "vagrant_context.h"

#include <cstdio>
#include <memory>

namespace {
int g_events[16] = {};
int g_eventCount = 0;
struct GuestCall {
  std::uint32_t address;
  std::uint32_t args[4];
  int arity;
};
GuestCall g_calls[64] = {};
int g_callCount = 0;
struct FileRead {
  std::uint32_t lba;
  std::uint32_t size;
  std::uint32_t destination;
};
FileRead g_fileReads[8] = {};
int g_fileReadCount = 0;
int g_cardStartCalls = 0;
bool g_titleStartupReady = false;
bool g_titleMenuReady = false;
bool g_battleReady = false;
bool g_titleMovieReady = false;
int g_initMemcardPoll = 0;
std::uint32_t g_memcardEvents[8] = {};
int g_memcardEventCount = 0;
int g_memcardEventIndex = 0;
std::uint32_t g_firstFileResult = 0u;

void record(int event) {
  g_events[g_eventCount++] = event;
}

void input(Core &) {
  record(1);
}
void audio(Core &) {
  record(2);
}
bool titleStartup(Core &) {
  record(3);
  return g_titleStartupReady;
}
bool titleMenu(Core &) {
  record(4);
  return g_titleMenuReady;
}
bool battle(Core &) {
  record(5);
  return g_battleReady;
}
bool titleMovie(Core &) {
  record(6);
  return g_titleMovieReady;
}
void present(Core &) {
  record(7);
}
void pace(Core &) {
  record(8);
}
void libDs(Core &) {
  record(9);
}
void resumeResident(Core &) {
  record(10);
}

std::uint32_t recordCall(std::uint32_t address,
                         int arity,
                         std::uint32_t a0 = 0,
                         std::uint32_t a1 = 0,
                         std::uint32_t a2 = 0,
                         std::uint32_t a3 = 0) {
  g_calls[g_callCount++] = {.address = address, .args = {a0, a1, a2, a3}, .arity = arity};
  if (address == vagrant::resident::kCardStart) {
    return g_cardStartCalls++ == 0 ? 1u : 0u;
  }
  if (address == vagrant::resident::kAllocHeapR) {
    return 0x80070000u + static_cast<std::uint32_t>(g_fileReadCount) * 0x10000u;
  }
  if (address == vagrant::title_memcard::kAllocHeap) {
    return 0x80090000u;
  }
  if (address == vagrant::title_memcard::kOpenEvent) {
    return 0x40u + static_cast<std::uint32_t>(g_callCount);
  }
  return 0;
}

void libDsCall0(Core &, std::uint32_t address) {
  recordCall(address, 0);
}

std::uint32_t guestCall0(Core &, std::uint32_t address) {
  return recordCall(address, 0);
}
std::uint32_t guestCall1(Core &, std::uint32_t address, std::uint32_t a0) {
  if (address == vagrant::title_memcard::kOwner && a0 == 0u) {
    recordCall(address, 1, a0);
    return g_initMemcardPoll++ == 0 ? 0u : 1u;
  }
  if (address == vagrant::title_save::kMemcardEventHandler && a0 == 0u) {
    recordCall(address, 1, a0);
    return g_memcardEventIndex < g_memcardEventCount ? g_memcardEvents[g_memcardEventIndex++] : 2u;
  }
  return recordCall(address, 1, a0);
}
std::uint32_t guestCall2(Core &, std::uint32_t address, std::uint32_t a0, std::uint32_t a1) {
  recordCall(address, 2, a0, a1);
  return address == vagrant::title_save::kFirstFile ? g_firstFileResult : 0u;
}
std::uint32_t
guestCall4(Core &core, std::uint32_t address, std::uint32_t a0, std::uint32_t a1, std::uint32_t a2, std::uint32_t a3) {
  const std::uint32_t result = recordCall(address, 4, a0, a1, a2, a3);
  if (address == vagrant::title_save::kRMemcpy) {
    for (std::uint32_t index = 0u; index < a2; ++index) {
      core.mem_w8(a0 + index, core.mem_r8(a1 + index));
    }
  }
  return result;
}

bool readFile(Core &, std::uint32_t lba, std::uint32_t size, std::uint32_t destination) {
  g_fileReads[g_fileReadCount++] = {.lba = lba, .size = size, .destination = destination};
  return true;
}

bool expectEvents(const int *expected, int count) {
  if (g_eventCount != count) {
    return false;
  }
  for (int i = 0; i < count; ++i) {
    if (g_events[i] != expected[i]) {
      return false;
    }
  }
  return true;
}

bool expectCallAddresses(const std::uint32_t *expected, int count) {
  if (g_callCount != count) {
    return false;
  }
  for (int i = 0; i < count; ++i) {
    if (g_calls[i].address != expected[i]) {
      return false;
    }
  }
  return true;
}
} // namespace

int main() {
  auto game = std::make_unique<Game>();
  vagrant::VagrantContext contextStorage;
  game->core.gameCtx = &contextStorage;
  auto *context = &contextStorage;
  context->libDsField = vagrant::cd::LibDsField({.call0 = libDsCall0});
  const vagrant::ResidentCallServices residentServices{
      .call0 = guestCall0,
      .call1 = guestCall1,
      .call2 = guestCall2,
      .call4 = guestCall4,
      .readFile = readFile,
  };
  context->residentPhase = vagrant::ResidentPhase(residentServices);
  context->titleSplash = vagrant::TitleSplashPhase(residentServices);
  context->titleSaveCheck = vagrant::TitleSaveCheck(residentServices);

  vagrant::FrameServices services{
      .input = input,
      .audio = audio,
      .titleStartup = titleStartup,
      .titleMenu = titleMenu,
      .battle = battle,
      .titleMovie = titleMovie,
      .present = present,
      .pace = pace,
      .libDs = libDs,
      .resumeResident = resumeResident,
  };
  vagrant::VagrantFrameDriver driver(services);
  game->core.r[29] = 0x801FFFF8u;
  const std::uint32_t initialStack = game->core.r[29];
  context->residentPhase.begin(game->core);
  const std::uint32_t bootCalls[] = {
      vagrant::resident::kCxxMain,
      vagrant::resident::kSetVideoMode,
      vagrant::resident::kSetDispMask,
      vagrant::resident::kResetCallback,
      vagrant::resident::kResetGraph,
      vagrant::resident::kSetGraphDebug,
      vagrant::resident::kCardStop,
  };
  if (!expectCallAddresses(bootCalls, 7) ||
      context->residentPhase.state() != vagrant::ResidentPhaseState::InitCardFieldWait ||
      game->core.r[29] != initialStack - 0x40u) {
    std::fprintf(stderr, "boot did not stop at InitCARD's exact native-owned field boundary\n");
    return 1;
  }
  g_eventCount = 0;
  driver.stepFrame(game->core, 41);
  const int residentEvents[] = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10};
  if (!expectEvents(residentEvents, 10) || driver.lastFieldOwner() != vagrant::FieldOwner::Resident ||
      game->timing.logicFrame != 41) {
    std::fprintf(stderr, "resident field did not own input/audio/arbitration/present/pace/resume exactly once\n");
    return 1;
  }

  g_battleReady = true;
  g_eventCount = 0;
  driver.stepFrame(game->core, 42);
  const int battleEvents[] = {1, 2, 3, 4, 5, 7, 8, 9, 10};
  if (!expectEvents(battleEvents, 9) || driver.lastFieldOwner() != vagrant::FieldOwner::Battle ||
      game->timing.logicFrame != 42) {
    std::fprintf(stderr, "BATTLE completed fence did not short-circuit TITLE movie and present once\n");
    return 1;
  }

  g_battleReady = false;
  g_titleMenuReady = true;
  g_eventCount = 0;
  driver.stepFrame(game->core, 43);
  const int titleEvents[] = {1, 2, 3, 4, 7, 8, 9, 10};
  if (!expectEvents(titleEvents, 8) || driver.lastFieldOwner() != vagrant::FieldOwner::Title ||
      game->timing.logicFrame != 43) {
    std::fprintf(stderr, "TITLE completed fence did not short-circuit later owners and present once\n");
    return 1;
  }

  // Exercise the real ResidentPhase body through its injected finite-call seam. InitCARD returns
  // after one host field, then _sysInit completes and TITLE reaches _displayLoadingScreen's VSync(2).
  g_callCount = 0;
  game->core.mem_w32(vagrant::cd::kSystemState, vagrant::cd::kSystemBusy);
  game->core.mem_w32(vagrant::cd::kCommandDeadline, 30u);
  context->residentPhase.advanceAfterField(game->core);
  if (context->residentPhase.state() != vagrant::ResidentPhaseState::LoadingScreenFieldWait ||
      context->residentPhase.loadingFieldsRemaining() != 2u ||
      game->core.mem_r32(vagrant::resident::kResetEnabled) != 1u ||
      game->core.mem_r32(vagrant::resident::kSaveGameClearData) != 0u || !context->libDsField.initialized() ||
      game->core.mem_r32(vagrant::cd::kSystemState) != vagrant::cd::kSystemReady ||
      game->core.mem_r32(vagrant::cd::kCommandDeadline) != 0u) {
    std::fprintf(stderr, "finite _sysInit did not reach TITLE's measured two-field loading wait\n");
    return 1;
  }
  g_callCount = 0;
  context->libDsField.serviceField(game->core);
  if (g_callCount != 1 || g_calls[0].address != vagrant::cd::kFieldStatusTick) {
    std::fprintf(stderr, "native field did not invoke the exact finite libds field services\n");
    return 1;
  }
  g_callCount = 0;
  context->residentPhase.advanceAfterField(game->core);
  if (g_callCount != 0 || context->residentPhase.loadingFieldsRemaining() != 1u) {
    std::fprintf(stderr, "VSync(2) did not retain its first complete native-owned field\n");
    return 1;
  }
  game->core.mem_w8(vagrant::resident::kLoadingImageHeader, 0x80u);
  game->core.mem_w8(vagrant::resident::kLoadingImageHeader + 1u, 0u);
  game->core.mem_w8(vagrant::resident::kLoadingImageHeader + 2u, 0x20u);
  game->core.mem_w8(vagrant::resident::kLoadingImageHeader + 3u, 0u);
  game->core.mem_w32(vagrant::cd::kDiskState, 0xFFFFFFFFu);
  game->core.mem_w32(vagrant::cd::kDiskState + 28u, 0xFFFFFFFFu);
  game->core.mem_w32(vagrant::cd::kDiskState + 44u, 0xFFFFFFFFu);
  game->core.mem_w32(vagrant::cd::kCdReadBuffer, 0xFFFFFFFFu);
  context->residentPhase.advanceAfterField(game->core);
  bool dispatchedMenuSound = false;
  int loadImageCalls = 0;
  int dsControlCalls = 0;
  int dsFlushCalls = 0;
  for (int i = 0; i < g_callCount; ++i) {
    dispatchedMenuSound |= g_calls[i].address == vagrant::resident::kLoadMenuSound;
    loadImageCalls += g_calls[i].address == vagrant::resident::kLoadImage ? 1 : 0;
    if (g_calls[i].address == vagrant::cd::kDsControlB) {
      const bool isPause =
          dsControlCalls == 0 && g_calls[i].arity == 2 && g_calls[i].args[0] == 9u && g_calls[i].args[1] == 0u;
      const bool isSetMode = dsControlCalls == 1 && g_calls[i].arity == 2 && g_calls[i].args[0] == 0x0Eu &&
                             g_calls[i].args[1] == vagrant::cd::kDsControlBuffer;
      if (!isPause && !isSetMode) {
        std::fprintf(stderr, "_diskReset did not preserve its exact blocking control ABI\n");
        return 1;
      }
      ++dsControlCalls;
    }
    dsFlushCalls += g_calls[i].address == vagrant::cd::kDsFlush ? 1 : 0;
  }
  if (context->residentPhase.state() != vagrant::ResidentPhaseState::DiskResetFieldWait || dispatchedMenuSound ||
      loadImageCalls != 2 || dsControlCalls != 2 || dsFlushCalls != 1 ||
      game->core.mem_r8(vagrant::cd::kDiskState + 1u) != 0x80u ||
      game->core.mem_r8(vagrant::cd::kDiskState + 28u) != 0x80u ||
      game->core.mem_r8(vagrant::cd::kDiskState + 2u) != 0u || game->core.mem_r8(vagrant::cd::kDiskState) != 0u ||
      game->core.mem_r32(vagrant::cd::kDiskState + 44u) != 0u || game->core.mem_r32(vagrant::cd::kCdReadBuffer) != 0u ||
      game->core.r[29] != initialStack - 0x48u) {
    std::fprintf(stderr, "TITLE loading field did not enter _diskReset's finite three-field wait\n");
    return 1;
  }

  const int callsBeforeDiskWait = g_callCount;
  context->residentPhase.advanceAfterField(game->core);
  context->residentPhase.advanceAfterField(game->core);
  if (context->residentPhase.state() != vagrant::ResidentPhaseState::DiskResetFieldWait ||
      g_callCount != callsBeforeDiskWait) {
    std::fprintf(stderr, "_diskReset VSync(3) did not retain two complete native-owned fields\n");
    return 1;
  }
  context->residentPhase.advanceAfterField(game->core);
  if (context->residentPhase.state() != vagrant::ResidentPhaseState::MenuSoundLoadFieldWait ||
      game->core.r[29] != initialStack - 0x48u) {
    std::fprintf(stderr, "_diskReset did not enter the first finite menu-sound read after three fields\n");
    return 1;
  }

  // Each real-disc native file copy completes before one explicit host field. The post-field half
  // applies the exact sound-bank consumer and starts the next copy without calling the retired
  // asynchronous libds queue or _loadMenuSound whole.
  for (int load = 0; load < 4; ++load) {
    context->residentPhase.advanceAfterField(game->core);
  }
  for (int i = 0; i < g_callCount; ++i) {
    dispatchedMenuSound |= g_calls[i].address == vagrant::resident::kLoadMenuSound;
  }
  const FileRead expectedReads[] = {
      {vagrant::resident::kWave0000Lba, vagrant::resident::kWave0000Size, 0u},
      {vagrant::resident::kWave0005Lba, vagrant::resident::kWave0005Size, 0u},
      {vagrant::resident::kWave0200Lba, vagrant::resident::kWave0200Size, 0u},
      {vagrant::resident::kEffect00Lba, vagrant::resident::kEffect00Size, vagrant::resident::kSfxData},
      {vagrant::resident::kTitlePrgLba, vagrant::resident::kTitlePrgSize, vagrant::resident::kTitleOverlayBase},
  };
  bool readsMatch = g_fileReadCount == 5;
  for (int index = 0; index < g_fileReadCount && index < 5; ++index) {
    readsMatch &= g_fileReads[index].lba == expectedReads[index].lba &&
                  g_fileReads[index].size == expectedReads[index].size &&
                  (index < 3 ? g_fileReads[index].destination != 0u
                             : g_fileReads[index].destination == expectedReads[index].destination);
  }
  if (context->residentPhase.state() != vagrant::ResidentPhaseState::TitleProgramLoadFieldWait || dispatchedMenuSound ||
      !readsMatch || game->core.r[29] != initialStack) {
    std::fprintf(stderr, "finite menu-sound loads did not load TITLE.PRG at the exact boundary\n");
    return 1;
  }
  g_callCount = 0;
  context->residentPhase.advanceAfterField(game->core);
  bool calledInitGameData = false;
  bool calledGuestVSync = false;
  for (int index = 0; index < g_callCount; ++index) {
    calledInitGameData |= g_calls[index].address == vagrant::title_splash::kInitGameData;
    calledGuestVSync |= g_calls[index].address == vagrant::sync::kVSync;
  }
  if (context->residentPhase.state() != vagrant::ResidentPhaseState::TitleSplashRunning ||
      context->titleSplash.state() != vagrant::TitleSplashState::InitialFieldWait || !calledInitGameData ||
      calledGuestVSync || game->core.mem_r32(vagrant::title_splash::kSettings) != 0x02D80130u ||
      game->core.mem_r8(vagrant::title_splash::kSettings + 8u) != 1u ||
      game->core.mem_r8(vagrant::title_splash::kSettings + 9u) != 3u) {
    std::fprintf(stderr, "TITLE.PRG did not enter the native-owned splash after one host field\n");
    return 1;
  }
  g_callCount = 0;
  context->titleSplash.advanceAfterField(game->core);
  bool calledPublisherSprite = false;
  calledGuestVSync = false;
  for (int index = 0; index < g_callCount; ++index) {
    calledPublisherSprite |= g_calls[index].address == vagrant::title_splash::kDrawSprite &&
                             g_calls[index].arity == 4 && g_calls[index].args[0] == 0x00580020u &&
                             g_calls[index].args[1] == 0x10140000u && g_calls[index].args[2] == 0x00300100u &&
                             g_calls[index].args[3] == 0x007C0005u;
    calledGuestVSync |= g_calls[index].address == vagrant::sync::kVSync;
  }
  if (context->titleSplash.state() != vagrant::TitleSplashState::PublisherFieldWait || !calledPublisherSprite ||
      calledGuestVSync || game->core.r[29] != initialStack - 0xB0u) {
    std::fprintf(stderr, "TITLE publisher splash did not advance one exact host-owned field\n");
    return 1;
  }

  // Complete both 364-field loops, then prove ResidentPhase begins the whole native save-file check
  // rather than dispatching _saveFileExists or gametimeUpdate through their guest VSync calls.
  for (std::uint32_t field = 0u; field < 728u; ++field) {
    g_callCount = 0;
    context->titleSplash.advanceAfterField(game->core);
  }
  if (!context->titleSplash.complete() || game->core.r[29] != initialStack) {
    std::fprintf(stderr, "TITLE splash did not complete both exact 364-field loops\n");
    return 1;
  }
  constexpr std::uint32_t kTemplate = 0x80070000u;
  constexpr char kFilename[] = "bu00:BASLUS-01040VAG0";
  game->core.mem_w32(vagrant::title_save::kFilenameTemplatePointer, kTemplate);
  for (std::uint32_t index = 0u; index < vagrant::title_save::kFilenameSize; ++index) {
    game->core.mem_w8(kTemplate + index, static_cast<std::uint8_t>(kFilename[index]));
  }
  game->core.mem_w8(vagrant::resident::kGameTimeTickSpeed, 2u);
  g_initMemcardPoll = 0;
  g_memcardEvents[0] = 0u; // port 1 pending
  g_memcardEvents[1] = 1u; // port 1 I/O complete
  g_memcardEvents[2] = 2u; // port 2 timed out
  g_memcardEventCount = 3;
  g_memcardEventIndex = 0;
  g_firstFileResult = 0u;
  g_callCount = 0;
  context->residentPhase.advanceAfterField(game->core);
  calledGuestVSync = false;
  bool dispatchedSaveOwner = false;
  bool dispatchedGameTime = false;
  for (int index = 0; index < g_callCount; ++index) {
    calledGuestVSync |= g_calls[index].address == vagrant::sync::kVSync;
    dispatchedSaveOwner |= g_calls[index].address == vagrant::title_save::kOwner;
    dispatchedGameTime |= g_calls[index].address == vagrant::title_save::kGameTimeUpdate;
  }
  if (context->residentPhase.state() != vagrant::ResidentPhaseState::TitleSaveCheckRunning ||
      context->titleSaveCheck.state() != vagrant::TitleSaveCheckState::InitFieldWait || calledGuestVSync ||
      dispatchedSaveOwner || dispatchedGameTime ||
      game->core.r[29] != initialStack - vagrant::title_save::kStackFrameSize) {
    std::fprintf(stderr, "TITLE did not split the whole save-file caller at its first native field\n");
    return 1;
  }
  for (int field = 0; field < 5; ++field) {
    g_callCount = 0;
    context->residentPhase.advanceAfterField(game->core);
    for (int index = 0; index < g_callCount; ++index) {
      if (g_calls[index].address == vagrant::sync::kVSync ||
          g_calls[index].address == vagrant::title_save::kGameTimeUpdate) {
        std::fprintf(stderr, "TITLE save-file phase dispatched a guest field owner\n");
        return 1;
      }
    }
  }
  const std::uint32_t filename =
      initialStack - vagrant::title_save::kStackFrameSize + vagrant::title_save::kFilenameOffset;
  if (!context->titleSaveCheck.complete() || context->titleSaveCheck.saveFileExists() ||
      game->core.r[29] != initialStack || game->core.mem_r8(vagrant::resident::kGameTime) != 4u ||
      game->core.mem_r8(filename + 2u) != static_cast<std::uint8_t>('0') ||
      game->core.mem_r8(filename + 20u) != static_cast<std::uint8_t>('?')) {
    std::fprintf(stderr, "TITLE save-file phase lost a memcard, gametime, filename, or stack transition\n");
    return 1;
  }
  if (context->residentPhase.state() != vagrant::ResidentPhaseState::TitleIntroBoundary) {
    std::fprintf(stderr, "TITLE save-file completion did not reach the intro ownership boundary\n");
    return 1;
  }

  // Exercise the native `_initMemcard` owner itself. It preserves the overlay pointer graph and
  // event lifecycle while replacing both interrupt-driven queue transfers with exact finite reads.
  g_callCount = 0;
  g_fileReadCount = 0;
  for (std::uint32_t index = 0u; index < 4u; ++index) {
    game->core.mem_w16(vagrant::title_memcard::kEventSpecs + index * 2u, static_cast<std::uint16_t>(0x100u + index));
  }
  vagrant::TitleMemcardInit memcardInit(residentServices);
  if (memcardInit.invoke(game->core, 1u) != 0u ||
      memcardInit.state() != vagrant::TitleMemcardInitState::FirstExtentReady || g_fileReadCount != 1 ||
      g_fileReads[0].lba != vagrant::title_memcard::kSpmcimgLba ||
      g_fileReads[0].size != vagrant::title_memcard::kSpmcimgSize || g_fileReads[0].destination != 0x80090000u ||
      game->core.mem_r32(vagrant::title_memcard::kSpmcimgPointer) != 0x80090000u ||
      game->core.mem_r32(vagrant::title_memcard::kMcdataPointer) !=
          0x80090000u + vagrant::title_memcard::kMcdataOffset ||
      game->core.mem_r32(vagrant::title_memcard::kTextTablePointer) !=
          0x80090000u + vagrant::title_memcard::kMcdataOffset + vagrant::title_memcard::kTextTableOffset ||
      game->core.mem_r32(vagrant::title_memcard::kSaveFileInfoPointer) !=
          0x80090000u + vagrant::title_memcard::kMcdataOffset + vagrant::title_memcard::kSaveFileInfoOffset ||
      game->core.mem_r32(vagrant::title_memcard::kDirectoryEntryPointer) !=
          0x80090000u + vagrant::title_memcard::kMcdataOffset + vagrant::title_memcard::kDirectoryEntryOffset ||
      game->core.mem_r8(vagrant::title_memcard::kInitState) != 0u) {
    std::fprintf(stderr, "native _initMemcard did not preserve its first extent and pointer graph\n");
    return 1;
  }
  if (memcardInit.invoke(game->core, 0u) != 0u ||
      memcardInit.state() != vagrant::TitleMemcardInitState::SecondExtentReady ||
      game->core.mem_r8(vagrant::title_memcard::kInitState) != 1u || g_callCount != 2 ||
      g_calls[1].address != vagrant::title_memcard::kDrawImage ||
      g_calls[1].args[0] != vagrant::title_memcard::kSpmcimgImageXy || g_calls[1].args[1] != 0x80090000u ||
      g_calls[1].args[2] != vagrant::title_memcard::kSpmcimgImageWh) {
    std::fprintf(stderr, "native _initMemcard did not preserve the SPMCIMG upload boundary\n");
    return 1;
  }
  if (memcardInit.invoke(game->core, 0u) != 0u ||
      memcardInit.state() != vagrant::TitleMemcardInitState::EventSetupReady || g_fileReadCount != 2 ||
      g_fileReads[1].lba != vagrant::title_memcard::kMcdataLba ||
      g_fileReads[1].size != vagrant::title_memcard::kMcdataAndMcmanSize ||
      g_fileReads[1].destination != 0x80090000u + vagrant::title_memcard::kMcdataOffset ||
      game->core.mem_r8(vagrant::title_memcard::kInitState) != 2u) {
    std::fprintf(stderr, "native _initMemcard did not preserve its contiguous MCDATA/MCMAN extent\n");
    return 1;
  }
  if (memcardInit.invoke(game->core, 0u) != 1u || memcardInit.state() != vagrant::TitleMemcardInitState::Complete ||
      g_callCount != 21) {
    std::fprintf(stderr, "native _initMemcard did not complete its event setup boundary\n");
    return 1;
  }
  for (std::uint32_t index = 0u; index < vagrant::title_memcard::kEventCount; ++index) {
    const GuestCall &opened = g_calls[4 + index];
    const std::uint32_t descriptor = game->core.mem_r32(vagrant::title_memcard::kEventDescriptors + index * 4u);
    const std::uint32_t expectedClass =
        (index & 4u) == 0u ? vagrant::title_memcard::kSwCardEvent : vagrant::title_memcard::kHwCardEvent;
    if (opened.address != vagrant::title_memcard::kOpenEvent || opened.args[0] != expectedClass ||
        opened.args[1] != 0x100u + (index & 3u) || opened.args[2] != vagrant::title_memcard::kEventModeNoInterrupt ||
        descriptor != 0x45u + index || g_calls[13 + index].address != vagrant::title_memcard::kEnableEvent ||
        g_calls[13 + index].args[0] != descriptor) {
      std::fprintf(stderr, "native _initMemcard changed the eight-event open/enable ABI\n");
      return 1;
    }
  }
  for (int index = 0; index < g_callCount; ++index) {
    const std::uint32_t address = g_calls[index].address;
    if (address == vagrant::sync::kVSync || address == vagrant::title_save::kProcessCdQueue ||
        address == vagrant::title_memcard::kAllocateCdQueueSlot ||
        address == vagrant::title_memcard::kFreeCdQueueSlot || address == vagrant::title_memcard::kCdEnqueue ||
        address == vagrant::title_memcard::kOwner) {
      std::fprintf(stderr, "native _initMemcard crossed its forbidden guest queue/VSync boundary\n");
      return 1;
    }
  }

  context->battleFrame.frameCompleted();
  if (!context->battleFrame.frameReady()) {
    std::fprintf(stderr, "VagrantContext did not retain BATTLE frame producer state\n");
    return 1;
  }
  context->titleMovie.frameCompleted();
  if (!context->titleMovie.frameReady()) {
    std::fprintf(stderr, "VagrantContext did not retain TITLE movie producer state\n");
    return 1;
  }
  context->titleMenu.frameCompleted();
  if (!context->titleMenu.frameReady()) {
    std::fprintf(stderr, "VagrantContext did not retain TITLE menu producer state\n");
    return 1;
  }

  std::puts("Vagrant native owners: finite TITLE reinitialisation, fatal guest VSync");
  return 0;
}
