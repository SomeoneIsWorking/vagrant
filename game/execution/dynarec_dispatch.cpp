#include "execution/dynarec_dispatch.h"

#include "core.h"
#include "guest_call.h"
#include "native_dispatch.h"
#include "resumable_guest_call.h"
#include "runtime/vagrant_context.h"

#include <lucent/log.h>

#include <cstdlib>

namespace vagrant::dynarec {

bool installNativeOverride(Core &core,
                           std::uint32_t address,
                           std::string_view name,
                           Override function,
                           psx::cpu::ImageIdentity expectedImage) {
  if (function == nullptr) {
    lucent::error("vagrant-dynarec", "override '{}' at 0x{:08X} has no handler; refusing to install", name, address);
    return false;
  }
  const auto image = core.currentImageIdentity(address);
  if (!image) {
    lucent::error("vagrant-dynarec",
                  "override '{}' at 0x{:08X} resolves to no unambiguous active image, so it is not this "
                  "title's leaf at that address; refusing rather than attributing it to whichever "
                  "module happens to be resident",
                  name,
                  address);
    return false;
  }
  if (expectedImage != psx::cpu::ImageIdentity{} && *image != expectedImage) {
    lucent::error("vagrant-dynarec",
                  "override '{}' at 0x{:08X} resolves to image {}/{}, not the generation this owner "
                  "publishes ({}/{}); refusing because a retired generation's key is unreachable by "
                  "construction and installing against the new one would own a different body",
                  name,
                  address,
                  image->id,
                  image->generation,
                  expectedImage.id,
                  expectedImage.generation);
    return false;
  }
  // Image and generation are checked; the framework refuses a key that already has an owner.
  return psx::cpu::tryInstallNativeOverride(core, address, name, function).has_value();
}

psx::cpu::ExecutionResult callGuest(Core &core, std::uint32_t address) {
  return psx::cpu::dispatchGuest(core, address, psx::cpu::ExecutionBudget::currentTurn(core));
}

std::uint32_t callReturning0(Core &core, std::uint32_t address) {
  psx::cpu::dispatchGuestToReturn0(core, address, psx::cpu::ExecutionBudget::currentTurn(core), "guest call0");
  return core.r[2];
}

std::uint32_t callReturning1(Core &core, std::uint32_t address, std::uint32_t a0) {
  psx::cpu::dispatchGuestToReturn1(core, address, a0, psx::cpu::ExecutionBudget::currentTurn(core), "guest call1");
  return core.r[2];
}

std::uint32_t callReturning2(Core &core, std::uint32_t address, std::uint32_t a0, std::uint32_t a1) {
  psx::cpu::dispatchGuestToReturn2(core, address, a0, a1, psx::cpu::ExecutionBudget::currentTurn(core), "guest call2");
  return core.r[2];
}

std::uint32_t callReturning4(
    Core &core, std::uint32_t address, std::uint32_t a0, std::uint32_t a1, std::uint32_t a2, std::uint32_t a3) {
  psx::cpu::dispatchGuestToReturn4(
      core, address, a0, a1, a2, a3, psx::cpu::ExecutionBudget::currentTurn(core), "guest call4");
  return core.r[2];
}

psx::cpu::ExecutionResult executeTurn(Core &core, std::uint32_t address) {
  return psx::cpu::dispatchGuestUntilExit(core, address, psx::cpu::ExecutionBudget::currentTurn(core));
}

psx::cpu::ExecutionResult callOriginal(Core &core, psx::cpu::NativeKey key) {
  return psx::cpu::callOriginal(core, key, psx::cpu::ExecutionBudget::currentTurn(core));
}

psx::cpu::ExecutionResult callOriginal(Core &core, std::uint32_t address) {
  return psx::cpu::callOriginal(core, address, psx::cpu::ExecutionBudget::currentTurn(core));
}

void callOriginalToReturn(Core &core, std::uint32_t address, std::string_view owner) {
  psx::cpu::callOriginalToReturn(core, address, psx::cpu::ExecutionBudget::currentTurn(core), owner);
}

psx::cpu::ExecutionResult callOriginalResuming(Core &core, psx::cpu::NativeKey key) {
  return psx::cpu::callOriginalResumingToExit(core, key, psx::cpu::ExecutionBudget::currentTurn(core));
}

std::uint32_t callGuestResumingToReturn(Core &core, std::uint32_t entry, std::uint32_t turnCap) {
  return psx::cpu::callGuestToReturnResuming(
      core, "Vagrant finite guest leaf", entry, core.r[31], std::nullopt, turnCap);
}

void requireGuestReturn(const psx::cpu::ExecutionResult &result, std::string_view owner) {
  if (psx::cpu::requireGuestReturn(result, owner)) {
    return;
  }
  std::abort();
}

bool hasNativeOverride(Core &core, psx::cpu::ImageIdentity image, std::uint32_t address) {
  if (image == psx::cpu::ImageIdentity{}) {
    return false;
  }
  if (core.currentImageIdentity(address) != image) {
    return false;
  }
  return core.nativeDispatcher().isInstalled({image, address});
}

} // namespace vagrant::dynarec
