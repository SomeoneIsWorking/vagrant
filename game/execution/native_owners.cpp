#include "execution/native_owners.h"

#include "boot/game_heap.h"
#include "cd/cd_facts.h"
#include "cd/ds_control.h"
#include "core.h"
#include "execution/dynarec_dispatch.h"
#include "render/battle_projection.h"
#include "runtime/vagrant_context.h"

#include <lucent/log.h>

namespace vagrant {
namespace {

// Runs the native allocator initialiser, then the original guest body for the rest of the function.
void initHeapOverride(Core *core) {
  const auto image = core->currentImageIdentity(heap::kInitHeap);
  heap::initHeap(core);
  if (!image) {
    lucent::warn("vagrant-heap",
                 "vs_main_initHeap ran with no active image at 0x{:08X}, so no original guest body was "
                 "reachable; the native free-list seed is in place and the guest's own remaining work "
                 "in that function did not run",
                 heap::kInitHeap);
    return;
  }
  const psx::cpu::NativeKey key{*image, heap::kInitHeap};
  // Resume across host turns if the original body needs more than one.
  const psx::cpu::ExecutionResult result = dynarec::callOriginalResuming(*core, key);
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
}

} // namespace

namespace {

// libds's blocking `DsControlB` spins in DS_getready -> DS_sync -> CD_sync (0x80020F28) on 0x800324D8, written only
// by libcd's CD interrupt handler, which nothing in the port raises.
void dsControlBOverride(Core *core) {
  cd::handleDsControlB(*core);
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
      {cd::kDsControlB, "Vagrant libds DsControlB", dsControlBOverride},
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
  // Projection publication leaves go through the same seam.
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
               "resident native owners registered against image {}/{}: {} of {} title leaf/leaves + "
               "4 measured projection publication leaves",
               residentImage.id,
               residentImage.generation,
               registration.installed,
               registration.attempts);
  return registration;
}

} // namespace vagrant
