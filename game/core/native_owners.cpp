#include "core/native_owners.h"

#include "core.h"
#include "core/dynarec_dispatch.h"
#include "core/game_heap.h"
#include "core/vagrant_context.h"
#include "render/battle_projection.h"

#include <lucent/log.h>

namespace vagrant {
namespace {

// The registered handler for the game's own allocator initialiser. It runs the VERIFIED native body
// (S007, measured byte-for-byte from the SHA-bound executable) and then re-enters the ORIGINAL guest body so the
// guest keeps whatever else that function does. `superCall` is the framework's one spelling of
// "execute the retail body with this override suppressed for one call", and it is what keeps this
// leaf a native/dynarec hybrid rather than a replacement of the guest.
void initHeapOverride(Core *core) {
  const auto image = core->currentImageIdentity(heap::kInitHeap);
  contextOf(*core).executionTelemetry.recordOverrideHit("vs_main_initHeap");
  heap::initHeap(core);
  if (image) {
    psx::cpu::ExecutionResult result = dynarec::callOriginal(*core, psx::cpu::NativeKey{*image, heap::kInitHeap});
    if (result.reason == psx::cpu::ExecutionExitReason::GuestReturn) {
      return;
    }
    // BudgetExhausted: the original body is still mid-function at a safe dispatcher boundary, so it
    // is resumed rather than abandoned. The framework's resume rule is that a function needing more
    // than one host turn is an ordinary bounded exit (see native_dispatch.h).
    while (result.reason == psx::cpu::ExecutionExitReason::BudgetExhausted) {
      result = psx::cpu::resumeOriginal(*core,
                                        psx::cpu::NativeKey{*image, heap::kInitHeap},
                                        result.guestPc,
                                        core->r[31],
                                        psx::cpu::ExecutionBudget::currentTurn(*core));
    }
    if (result.reason == psx::cpu::ExecutionExitReason::GuestReturn) {
      return;
    }
    lucent::error("vagrant-heap",
                  "vs_main_initHeap: the original guest body at 0x{:08X} exited as {} at 0x{:08X} after {} "
                  "cycles instead of returning; the native free-list seed is not a substitute for the "
                  "rest of that function",
                  heap::kInitHeap,
                  psx::cpu::executionExitName(result.reason),
                  result.guestPc,
                  result.cycles);
    return;
  }
  lucent::warn("vagrant-heap",
               "vs_main_initHeap ran with no active image at 0x{:08X}, so no original guest body was "
               "reachable; the native free-list seed is in place and the guest's own remaining work "
               "in that function did not run",
               heap::kInitHeap);
}

} // namespace

NativeOwnerRegistration installResidentNativeOwners(Core &core, psx::cpu::ImageIdentity residentImage) {
  NativeOwnerRegistration registration;
  const struct Binding {
    std::uint32_t address;
    const char *owner;
    psx::cpu::NativeFunction function;
  } bindings[]{
      {heap::kInitHeap, "Vagrant vs_main_initHeap", initHeapOverride},
  };
  for (const Binding &binding : bindings) {
    ++registration.attempts;
    if (dynarec::installNativeOverride(core, binding.address, binding.owner, binding.function, residentImage)) {
      ++registration.installed;
      continue;
    }
    ++registration.refused;
    registration.refusedOwner = binding.owner;
  }
  // The projection publication leaves are owned by the projection owner, which measures the guest's
  // viewport publication. They are registered through the same seam, so a refusal here is reported by
  // the same census.
  if (!installBattleProjection(core, residentImage)) {
    ++registration.refused;
    registration.refusedOwner = "Vagrant guest projection publication";
  }
  if (!registration) {
    lucent::error("vagrant-owners",
                  "resident native owners: installed {} of {} attempted leaf/leaves; {} refused, first "
                  "at '{}'",
                  registration.installed,
                  registration.attempts,
                  registration.refused,
                  registration.refusedOwner);
    return registration;
  }
  lucent::info("vagrant-owners",
               "resident native owners registered against image {}/{}: {} allocator leaf + 4 measured "
               "projection publication leaves",
               residentImage.id,
               residentImage.generation,
               registration.installed);
  return registration;
}

} // namespace vagrant
