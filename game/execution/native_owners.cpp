#include "execution/native_owners.h"

#include "boot/game_heap.h"
#include "boot/resident_facts.h"
#include "cd/cd_facts.h"
#include "cd/ds_control.h"
#include "core.h"
#include "execution/dynarec_dispatch.h"
#include "images/battle_transfer.h"
#include "render/battle_projection.h"
#include "runtime/vagrant_context.h"

#include <cstdlib>
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

// libds's blocking `DsControl`/`DsControlB` spin in DS_getready -> DS_sync -> CD_sync (0x80020F28) on 0x800324D8,
// written only by libcd's CD interrupt handler, which nothing in the port raises.
void dsControlOverride(Core *core) {
  cd::handleDsControl(*core);
}

// ds_cbready: the command's completion is owed before its first sector, which instant reads would otherwise put first.
void dsReadyOverride(Core *core) {
  const std::uint32_t intr = core->r[4];
  const std::uint32_t result = core->r[5];
  const std::uint32_t returnAddress = core->r[31];
  contextOf(*core).libDsField.completeOwedCommand(*core);
  core->r[4] = intr;
  core->r[5] = result;
  core->r[31] = returnAddress;
  dynarec::callOriginalToReturn(*core, cd::kDsReadyCallback, "Vagrant libds ds_cbready");
}

} // namespace

namespace {

// `_loadBattlePrg` waits on the CD queue for both overlays; the finite read publishes them whole instead, and the
// trailing `vs_overlay_wait` is a 4096-instruction nop sled.
void loadBattleProgramsOverride(Core *core) {
  const OverlayLoadResult loaded = readAndLoadBattle(*core, contextOf(*core).overlayImages, cd::readDiscSector);
  if (loaded) {
    lucent::info("vagrant-owners", "BATTLE.PRG and INITBTL.PRG loaded as published images");
    return;
  }
  lucent::error("vagrant-owners", "BATTLE.PRG/INITBTL.PRG load refused: {}", loaded.detail);
  std::abort();
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
      {cd::kDsControl, "Vagrant libds DsControl", dsControlOverride},
      {cd::kDsControlB, "Vagrant libds DsControlB", dsControlOverride},
      {cd::kDsReadyCallback, "Vagrant libds ds_cbready", dsReadyOverride},
      {resident::kLoadBattlePrg, "Vagrant _loadBattlePrg", loadBattleProgramsOverride},
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
