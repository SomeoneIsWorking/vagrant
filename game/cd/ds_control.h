#pragma once

class Core;

namespace vagrant::cd {

// Native body for the blocking `DsControlB`; unsupported commands are refused by name.
void handleDsControlB(Core &core);

} // namespace vagrant::cd