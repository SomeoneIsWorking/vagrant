#pragma once

#include <cstdint>

class Core;

namespace vagrant::cd {

// Read one measured resident file extent from the real disc into guest RAM. This is the finite
// title-owned replacement for Vagrant's libds ReadN callback chain under psxport's synchronous CD
// contract; success means every requested byte was copied from the CHD.
bool readNativeFile(Core &core, std::uint32_t lba, std::uint32_t size, std::uint32_t destination);

} // namespace vagrant::cd
