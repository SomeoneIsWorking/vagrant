#pragma once

class Core;

namespace vagrant::cd {

// Native body for the blocking `DsControl` and `DsControlB`; unsupported commands are refused by name.
void handleDsControl(Core &core);

} // namespace vagrant::cd