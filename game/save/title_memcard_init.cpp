#include "save/title_memcard_init.h"

#include "core.h"
#include "save/title_memcard_facts.h"
#include "vagrant_context.h"

#include <cstdlib>
#include <lucent/log.h>

namespace vagrant {

TitleMemcardInit::TitleMemcardInit() : TitleMemcardInit(productionResidentCallServices()) {}

TitleMemcardInit::TitleMemcardInit(ResidentCallServices services) : services_(services) {
  if (!services_.call0 || !services_.call1 || !services_.call4 || !services_.readFile) {
    lucent::error("vagrant-title-save", "TitleMemcardInit requires finite call and disc-read services");
    std::abort();
  }
}

void TitleMemcardInit::begin(Core &core) {
  const std::uint32_t spmcimg = services_.call1(core, title_memcard::kAllocHeap, title_memcard::kSpmcimgSize);
  if (spmcimg == 0u) {
    lucent::error("vagrant-title-save", "TITLE memory-card workspace allocation failed");
    std::abort();
  }
  const std::uint32_t mcdata = spmcimg + title_memcard::kMcdataOffset;
  core.mem_w32(title_memcard::kSpmcimgPointer, spmcimg);
  core.mem_w32(title_memcard::kMcdataPointer, mcdata);
  core.mem_w32(title_memcard::kTextTablePointer, mcdata + title_memcard::kTextTableOffset);
  core.mem_w32(title_memcard::kSaveFileInfoPointer, mcdata + title_memcard::kSaveFileInfoOffset);
  core.mem_w32(title_memcard::kDirectoryEntryPointer, mcdata + title_memcard::kDirectoryEntryOffset);
  core.mem_w8(title_memcard::kInitState, 0u);
  if (!services_.readFile(core, title_memcard::kSpmcimgLba, title_memcard::kSpmcimgSize, spmcimg)) {
    lucent::error("vagrant-title-save", "TITLE SPMCIMG.BIN native read failed");
    std::abort();
  }
  state_ = TitleMemcardInitState::FirstExtentReady;
}

void TitleMemcardInit::finishFirstExtent(Core &core) {
  services_.call4(core,
                  title_memcard::kDrawImage,
                  title_memcard::kSpmcimgImageXy,
                  core.mem_r32(title_memcard::kSpmcimgPointer),
                  title_memcard::kSpmcimgImageWh,
                  0u);
  core.mem_w8(title_memcard::kInitState, 1u);
  state_ = TitleMemcardInitState::SecondExtentReady;
}

void TitleMemcardInit::finishSecondExtent(Core &core) {
  const std::uint32_t mcdata = core.mem_r32(title_memcard::kMcdataPointer);
  if (!services_.readFile(core, title_memcard::kMcdataLba, title_memcard::kMcdataAndMcmanSize, mcdata)) {
    lucent::error("vagrant-title-save", "TITLE MCDATA.BIN/MCMAN.BIN native read failed");
    std::abort();
  }
  core.mem_w8(title_memcard::kInitState, 2u);
  state_ = TitleMemcardInitState::EventSetupReady;
}

void TitleMemcardInit::setupEvents(Core &core) {
  services_.call1(core, title_memcard::kEnableReset, 0u);
  services_.call0(core, title_memcard::kEnterCriticalSection);
  for (std::uint32_t index = 0u; index < title_memcard::kEventCount; ++index) {
    const std::uint32_t eventClass = (index & 4u) == 0u ? title_memcard::kSwCardEvent : title_memcard::kHwCardEvent;
    const std::uint32_t spec = core.mem_r16(title_memcard::kEventSpecs + (index & 3u) * 2u);
    const std::uint32_t descriptor =
        services_.call4(core, title_memcard::kOpenEvent, eventClass, spec, title_memcard::kEventModeNoInterrupt, 0u);
    core.mem_w32(title_memcard::kEventDescriptors + index * 4u, descriptor);
  }
  services_.call0(core, title_memcard::kExitCriticalSection);
  for (std::uint32_t index = 0u; index < title_memcard::kEventCount; ++index) {
    services_.call1(core, title_memcard::kEnableEvent, core.mem_r32(title_memcard::kEventDescriptors + index * 4u));
  }
  state_ = TitleMemcardInitState::Complete;
}

std::uint32_t TitleMemcardInit::invoke(Core &core, std::uint32_t init) {
  if (init != 0u) {
    begin(core);
    return 0u;
  }
  if (state_ == TitleMemcardInitState::FirstExtentReady) {
    finishFirstExtent(core);
    return 0u;
  }
  if (state_ == TitleMemcardInitState::SecondExtentReady) {
    finishSecondExtent(core);
    return 0u;
  }
  if (state_ == TitleMemcardInitState::EventSetupReady) {
    setupEvents(core);
    return 1u;
  }
  if (state_ == TitleMemcardInitState::Complete) {
    return 1u;
  }
  lucent::error("vagrant-title-save", "TITLE _initMemcard polled before initialization");
  std::abort();
}

} // namespace vagrant
