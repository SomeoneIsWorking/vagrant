#pragma once

class Core;

namespace vagrant::cd {

// libcd's CD_cw: the stock synchronous controller applies the command, then libds is owed its completion callback.
void handleCdCommand(Core *core);

} // namespace vagrant::cd
