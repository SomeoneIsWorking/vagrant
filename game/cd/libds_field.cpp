#include "cd/libds_field.h"

#include "cd/cd_facts.h"
#include "core.h"
#include "execution/dynarec_dispatch.h"
#include "game.h"

#include <cstdlib>
#include <lucent/log.h>

namespace vagrant::cd {

LibDsFieldServices productionLibDsFieldServices() {
  return {.call0 = dynarec::callReturning0, .call2 = dynarec::callReturning2};
}

LibDsField::LibDsField() : LibDsField(productionLibDsFieldServices()) {
}

LibDsField::LibDsField(LibDsFieldServices services) : services_(services) {
  requireServices(services_);
}

void LibDsField::requireServices(const LibDsFieldServices &services) {
  if (services.call0 && services.call2) {
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

  // Retail reaches Ready via the command callback; staying Busy would block the first ReadN.
  core.mem_w32(kSystemState, kSystemReady);
  core.mem_w32(kCommandDeadline, 0u);
  initialized_ = true;
}

void LibDsField::serviceField(Core &core) {
  if (!initialized_) {
    return;
  }
  completeOwedCommand(core);
  services_.call0(core, kFieldStatusTick);
}

void LibDsField::completeOwedCommand(Core &core) {
  if (!completionOwed_) {
    return;
  }
  completionOwed_ = false;
  const std::uint32_t callback = core.mem_r32(kSyncCallbackSlot);
  if (callback == 0u) {
    return;
  }
  // The instant controller finishes every command in one field with a zeroed result and its drive status.
  for (std::uint32_t index = 0; index < 8u; ++index) {
    core.mem_w8(kSyncResult + index, index == 0u ? core.game->cdc.stat : 0u);
  }
  core.mem_w8(kSyncInterruptCode, static_cast<std::uint8_t>(kCdlComplete));
  services_.call2(core, callback, kCdlComplete, kSyncResult);
}

} // namespace vagrant::cd
