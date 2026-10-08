#pragma once

#include "execution_exit.h"
#include "image_identity.h"

#include <string>

class Core;

namespace vagrant {

// Admits only the direct call from the resident generation into the just-published TITLE generation.
std::string validateTitleEntry(Core &core, psx::cpu::ImageIdentity residentImage, psx::cpu::ImageIdentity titleImage);

// Ordinary dynarec dispatch owns the call: it does not resume until the body returns, and the typed exit is the
// caller's.
psx::cpu::ExecutionResult
enterTitle(Core &core, psx::cpu::ImageIdentity residentImage, psx::cpu::ImageIdentity titleImage);

} // namespace vagrant