#include "title_entry.h"

#include "core.h"
#include "native_dispatch.h"
#include "resident_facts.h"

namespace vagrant {

std::string validateTitleEntry(Core &core, psx::cpu::ImageIdentity residentImage, psx::cpu::ImageIdentity titleImage) {
  if (core.pc != resident::kTitleCallSite) {
    return "resident PC is not at the measured TITLE call site";
  }
  if (core.currentImageIdentity(resident::kTitleCallSite) != residentImage) {
    return "resident call site belongs to a different image generation";
  }
  if (core.currentImageIdentity(resident::kTitleEntry) != titleImage) {
    return "TITLE entry belongs to a different image generation";
  }
  constexpr std::uint32_t kJalOpcode = 0x0C000000u;
  constexpr std::uint32_t kJalTargetMask = 0x03FFFFFFu;
  const std::uint32_t expectedCall = kJalOpcode | ((resident::kTitleEntry >> 2u) & kJalTargetMask);
  if (core.mem_r32(resident::kTitleCallSite) != expectedCall ||
      core.mem_r32(resident::kTitleCallSite + 4u) != resident::kTitleCallDelayWord) {
    return "resident TITLE call or delay slot differs from the measured executable";
  }
  return {};
}

psx::cpu::ExecutionResult enterTitle(Core &core,
                                     psx::cpu::ImageIdentity residentImage,
                                     psx::cpu::ImageIdentity titleImage,
                                     psx::cpu::ExecutionBudget budget) {
  const std::string refusal = validateTitleEntry(core, residentImage, titleImage);
  if (!refusal.empty()) {
    return {psx::cpu::ExecutionExitReason::Fault, core.pc, 0, refusal};
  }
  return psx::cpu::dispatchGuestUntilExit(core, core.pc, budget);
}

} // namespace vagrant
