#include "core/dynarec_dispatch.h"

#include "core.h"
#include "core/vagrant_context.h"

#include <lucent/log.h>

#include <cstdlib>

namespace vagrant::dynarec {
namespace {

// Telemetry is a per-Core product, and a Core that has no VagrantContext is a composition defect
// that `contextOf` already refuses. Reaching for the counters must not be a second, quieter copy of
// that decision, so the recording helpers go through the one accessor.
void recordInstall(Core &core, bool hadActiveImage, bool accepted) {
  contextOf(core).executionTelemetry.recordOverrideInstall(hadActiveImage, accepted);
}

} // namespace

bool installNativeOverride(Core &core,
                           std::uint32_t address,
                           std::string_view name,
                           Override function,
                           psx::cpu::ImageIdentity expectedImage) {
  if (function == nullptr) {
    lucent::error("vagrant-dynarec", "override '{}' at 0x{:08X} has no handler; refusing to install", name, address);
    recordInstall(core, false, false);
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
    recordInstall(core, false, false);
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
    recordInstall(core, true, false);
    return false;
  }
  // The image is resolved and the generation checked, so what remains is the framework's rule: build
  // the (identity, address) key and refuse a key that already has an owner.
  const bool accepted = psx::cpu::tryInstallNativeOverride(core, address, name, function).has_value();
  recordInstall(core, true, accepted);
  return accepted;
}

psx::cpu::ExecutionResult callGuest(Core &core, std::uint32_t address) {
  const auto result = psx::cpu::dispatchGuest(core, address, psx::cpu::ExecutionBudget::currentTurn(core));
  contextOf(core).executionTelemetry.recordDispatch(result.reason);
  return result;
}

psx::cpu::ExecutionResult executeTurn(Core &core, std::uint32_t address) {
  const auto result = psx::cpu::dispatchGuestUntilExit(core, address, psx::cpu::ExecutionBudget::currentTurn(core));
  contextOf(core).executionTelemetry.recordDispatch(result.reason);
  return result;
}

psx::cpu::ExecutionResult callOriginal(Core &core, psx::cpu::NativeKey key) {
  const auto result = psx::cpu::callOriginal(core, key, psx::cpu::ExecutionBudget::currentTurn(core));
  auto &telemetry = contextOf(core).executionTelemetry;
  telemetry.recordOriginalCall(result.reason);
  telemetry.recordDispatch(result.reason);
  return result;
}

psx::cpu::ExecutionResult callOriginal(Core &core, std::uint32_t address) {
  const auto result = psx::cpu::callOriginal(core, address, psx::cpu::ExecutionBudget::currentTurn(core));
  auto &telemetry = contextOf(core).executionTelemetry;
  telemetry.recordOriginalCall(result.reason);
  telemetry.recordDispatch(result.reason);
  return result;
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
