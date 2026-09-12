#pragma once

#include "execution_exit.h"
#include "image_identity.h"

#include <cstdint>
#include <string>

class Core;

namespace vagrant {

// The resident loader has already returned with TITLE.PRG published. Admit only its measured
// direct call from the still-active resident generation into the just-published TITLE generation.
std::string validateTitleEntry(Core &core, psx::cpu::ImageIdentity residentImage, psx::cpu::ImageIdentity titleImage);

// Once admitted, ordinary psxport dynarec dispatch owns the call, delay slot, TITLE body, and
// subsequent resident continuation. The budget is the caller's bounded runtime turn.
psx::cpu::ExecutionResult enterTitle(Core &core,
                                     psx::cpu::ImageIdentity residentImage,
                                     psx::cpu::ImageIdentity titleImage,
                                     psx::cpu::ExecutionBudget budget);

} // namespace vagrant
