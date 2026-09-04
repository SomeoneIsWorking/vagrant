#include "save/title_save_check.h"

#include "core.h"
#include "core/game_time.h"
#include "save/title_memcard_facts.h"
#include "save/title_save_facts.h"

#include <cstdlib>
#include <lucent/log.h>

namespace vagrant {

TitleSaveCheck::TitleSaveCheck() : TitleSaveCheck(productionResidentCallServices()) {}

TitleSaveCheck::TitleSaveCheck(ResidentCallServices services) : services_(services) {
  if (!services_.call0 || !services_.call1 || !services_.call2 || !services_.call4) {
    lucent::error("vagrant-title-save", "TitleSaveCheck requires every finite guest-call service");
    std::abort();
  }
}

void TitleSaveCheck::begin(Core &core) {
  if (state_ != TitleSaveCheckState::Cold) {
    lucent::error("vagrant-title-save", "TITLE save-file check began more than once");
    std::abort();
  }
  core.r[29] -= title_save::kStackFrameSize;
  services_.call1(core, title_memcard::kOwner, 1u);
  state_ = TitleSaveCheckState::InitFieldWait;
}

void TitleSaveCheck::beginPort(Core &core, std::uint32_t port) {
  port_ = port;
  services_.call1(core, title_save::kMemcardEventHandler, port_);
  eventState_ = services_.call1(core, title_save::kMemcardEventHandler, 0u) & 3u;
  state_ = TitleSaveCheckState::EventFieldWait;
}

void TitleSaveCheck::finish(Core &core, bool exists) {
  services_.call0(core, title_save::kShutdownMemcard);
  core.r[29] += title_save::kStackFrameSize;
  saveFileExists_ = exists;
  state_ = TitleSaveCheckState::Complete;
}

void TitleSaveCheck::finishInitField(Core &core) {
  // vs_main_gametimeUpdate(2) resumes here after its host-owned field. Preserve every tail effect;
  // only the VSync call itself is replaced by the return to VagrantFrameDriver.
  services_.call0(core, title_save::kAsmNop);
  services_.call0(core, title_save::kProcessCdQueue);
  game_time::advance(core);
  if (services_.call1(core, title_memcard::kOwner, 0u) == 0u) {
    return;
  }
  beginPort(core, 1u);
}

void TitleSaveCheck::finishEventField(Core &core) {
  constexpr std::uint32_t kEventPending = 0u;
  constexpr std::uint32_t kEventIoEnd = 1u;
  if (eventState_ == kEventPending) {
    eventState_ = services_.call1(core, title_save::kMemcardEventHandler, 0u) & 3u;
    return;
  }
  if (eventState_ == kEventIoEnd) {
    const std::uint32_t filename = core.r[29] + title_save::kFilenameOffset;
    const std::uint32_t directoryEntry = core.r[29] + title_save::kDirectoryEntryOffset;
    const std::uint32_t templateAddress = core.mem_r32(title_save::kFilenameTemplatePointer);
    services_.call4(core, title_save::kRMemcpy, filename, templateAddress, title_save::kFilenameSize, 0u);
    core.mem_w8(filename + 2u, static_cast<std::uint8_t>(port_ + static_cast<std::uint32_t>('/')));
    core.mem_w8(filename + 20u, static_cast<std::uint8_t>('?'));
    if (services_.call2(core, title_save::kFirstFile, filename, directoryEntry) != 0u) {
      finish(core, true);
      return;
    }
  }
  if (port_ < 2u) {
    beginPort(core, port_ + 1u);
    return;
  }
  finish(core, false);
}

void TitleSaveCheck::advanceAfterField(Core &core) {
  if (state_ == TitleSaveCheckState::InitFieldWait) {
    finishInitField(core);
  } else if (state_ == TitleSaveCheckState::EventFieldWait) {
    finishEventField(core);
  }
}

} // namespace vagrant
