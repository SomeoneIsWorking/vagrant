#include "cd/cd_command.h"

#include "cd_control.h"
#include "core.h"
#include "runtime/vagrant_context.h"

namespace vagrant::cd {

void handleCdCommand(Core *core) {
  cd_command_stock_sync(core);
  // CD_cw returns 0 once the command is accepted.
  if (core->r[2] == 0u) {
    contextOf(*core).libDsField.commandSent();
  }
}

} // namespace vagrant::cd
