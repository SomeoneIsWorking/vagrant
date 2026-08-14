// Vagrant's smallest coherent synchronous libds owner.
//
// Own DsControlB, the blocking CONTROL wrapper, rather than _diskReset or the
// asynchronous libds queue. The original recompiled body remains linked for
// A/B/oracle use. Async DsCommand/DsPacket, callbacks, query results, reads,
// and XA streaming remain guest-owned until their contracts are measured;
// reaching one here refuses instead of reporting fabricated success.
#include "cd_control.h"
#include "core.h"
#include "ds_control_contract.h"
#include "override_registry.h"
#include <cstdlib>
#include <lucent/log.h>

extern void gen_func_80025BE4(Core *);
extern void shard_set_override(uint32_t, void (*)(Core *));

namespace {
constexpr uint32_t kDsControlB = 0x80025BE4u;

void ds_control_b(Core *c) {
  const uint32_t cmd = c->r[4] & 0xFFu;
  const uint32_t param = c->r[5];
  const uint32_t result = c->r[6];
  if (!vagrant_cd::ownedControl(cmd)) {
    lucent::error("vagrant-cd",
                  "DsControlB REFUSED command 0x{:02X} param=0x{:08X} "
                  "result=0x{:08X}: query/read/result semantics are not owned",
                  cmd, param, result);
    std::abort();
  }
  if ((cmd == 0x02u || cmd == 0x0Du || cmd == 0x0Eu) && !param) {
    lucent::error(
        "vagrant-cd",
        "DsControlB REFUSED command 0x{:02X}: required parameter is null", cmd);
    std::abort();
  }
  lucent::debug("vagrant-cd",
                "DsControlB command 0x{:02X} param=0x{:08X} result=0x{:08X}",
                cmd, param, result);
  cd_control_sync(c);
}
} // namespace

void vagrant_cd_register_overrides() {
  overrides::install(kDsControlB, "VagrantCd::DsControlB", ds_control_b,
                     gen_func_80025BE4, shard_set_override);
}
