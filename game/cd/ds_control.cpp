// Vagrant's smallest coherent synchronous libds owner.
//
// Own DsControlB, the blocking CONTROL wrapper, rather than _diskReset or the asynchronous libds
// queue. Async DsCommand/DsPacket, callbacks, query results, reads, and XA streaming remain
// guest-owned until their contracts are measured; reaching one here refuses instead of reporting
// fabricated success.
#include "cd/cd_facts.h"
#include "cd/ds_control.h"
#include "cd_control.h"
#include "core.h"
#include "ds_control_contract.h"
#include <cstdlib>
#include <lucent/log.h>

void vagrant::cd::handleDsControlB(Core &core) {
  Core *c = &core;
  const uint32_t cmd = c->r[4] & 0xFFu;
  const uint32_t param = c->r[5];
  const uint32_t result = c->r[6];
  if (!vagrant_cd::ownedControl(cmd)) {
    lucent::error("vagrant-cd",
                  "DsControlB REFUSED command 0x{:02X} param=0x{:08X} "
                  "result=0x{:08X}: query/read/result semantics are not owned",
                  cmd,
                  param,
                  result);
    std::abort();
  }
  if ((cmd == 0x02u || cmd == 0x0Du || cmd == 0x0Eu) && !param) {
    lucent::error("vagrant-cd", "DsControlB REFUSED command 0x{:02X}: required parameter is null", cmd);
    std::abort();
  }
  lucent::debug("vagrant-cd", "DsControlB command 0x{:02X} param=0x{:08X} result=0x{:08X}", cmd, param, result);
  cd_control_sync(c);
  // DsControlB is blocking: the retail wrapper does not return until this command has completed.
  // The native controller completes it synchronously, so preserve the same libds postcondition
  // instead of leaving the previous command's retry deadline armed across the return.
  c->mem_w32(vagrant::cd::kSystemState, vagrant::cd::kSystemReady);
  c->mem_w32(vagrant::cd::kCommandDeadline, 0u);
}
