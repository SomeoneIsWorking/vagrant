#include "cd/libds_field.h"

#include "cd/cd_facts.h"
#include "core.h"
#include "guest_call.h"

#include <cstdlib>
#include <lucent/log.h>

namespace {

void call0(Core &core, std::uint32_t address) {
  rc0(&core, address);
}

} // namespace

namespace vagrant::cd {

LibDsFieldServices productionLibDsFieldServices() {
  return {.call0 = call0};
}

LibDsField::LibDsField() : LibDsField(productionLibDsFieldServices()) {}

LibDsField::LibDsField(LibDsFieldServices services) : services_(services) {
  requireServices(services_);
}

void LibDsField::requireServices(const LibDsFieldServices &services) {
  if (services.call0) {
    return;
  }
  lucent::error("vagrant-libds", "LibDsField requires its finite guest-call service");
  std::abort();
}

void LibDsField::completeSynchronousInit(Core &core) {
  if (initialized_) {
    lucent::error("vagrant-libds", "synchronous DsInit completed more than once");
    std::abort();
  }

  const std::uint32_t state = core.mem_r32(kSystemState);
  if (state != kSystemBusy) {
    lucent::error("vagrant-libds", "synchronous DsInit returned with state {} instead of Busy", state);
    std::abort();
  }

  // Retail reaches this exact Ready state through the low-level command callback. The native CD
  // leaves complete those commands before returning, so leaving Busy here would falsely retain an
  // asynchronous completion that no longer exists and prevent the first ReadN from being issued.
  core.mem_w32(kSystemState, kSystemReady);
  core.mem_w32(kCommandDeadline, 0u);
  initialized_ = true;
}

void LibDsField::serviceField(Core &core) {
  if (!initialized_) {
    return;
  }
  services_.call0(core, kFieldStatusTick);
}

} // namespace vagrant::cd
