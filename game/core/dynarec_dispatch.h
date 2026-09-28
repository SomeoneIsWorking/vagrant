#pragma once

#include "execution_exit.h"
#include "image_identity.h"
#include "native_dispatch.h"

#include <cstdint>
#include <string_view>

class Core;

namespace vagrant::dynarec {

// The title's whole adapter surface over psxport's per-Core dynarec executor, in five operations.
// It exists so no other module spells a budget, resolves an image identity, or chooses a dispatch
// form: `ExecutionBudget::currentTurn` is the ONE budget policy in the framework, and a second copy
// of it in this repository would be a second answer to "how long may a turn run".
//
// NOTHING HERE SELECTS AN EXECUTION ENGINE. Every path below is psxport's Lightrec executor; a
// missing or unavailable backend is a named failure at the product boundary, never a fallback mode.

using Override = psx::cpu::NativeFunction;

// Install one native leaf against the image generation that currently owns `address`.
//
// An address alone does not identify PSX code here: BATTLE, TITLE and ENDING all load at
// 0x80068800. This resolves the active identity first and REFUSES BY NAME, with the address, when
// there is no single owning image — because installing a leaf against an ambiguous or absent image is
// how a resident override would be attributed to an overlay's bytes. The refusal is counted in the
// per-Core telemetry, so a run that installed nothing cannot report the same numbers as a run that
// never tried.
bool installNativeOverride(Core &core,
                           std::uint32_t address,
                           std::string_view name,
                           Override function,
                           psx::cpu::ImageIdentity expectedImage = {});

// One finite guest call, resumed until it returns. The title calls finite leaves through this.
psx::cpu::ExecutionResult callGuest(Core &core, std::uint32_t address);

// One bounded guest turn, which may end in any typed exit. Used where the guest body is not
// guaranteed to return, so the caller handles the exit reason instead of assuming one.
psx::cpu::ExecutionResult executeTurn(Core &core, std::uint32_t address);

// Re-enter a guest body through the executor from inside a native owner, suppressing only the
// override key named by `key` for the dynamic extent of that one call.
psx::cpu::ExecutionResult callOriginal(Core &core, psx::cpu::NativeKey key);
psx::cpu::ExecutionResult callOriginal(Core &core, std::uint32_t address);

// Terminate the process when a leaf that was declared finite did not return. An unreachable
// diagnostic that reaches here has a real bug upstream, and a silent continue would ship a boot that
// stopped being measurable.
void requireGuestReturn(const psx::cpu::ExecutionResult &result, std::string_view owner);

// `true` when the address is the entry of an installed native leaf in the image generation that owns
// it right now. This is the title's own reading of "the override is reachable"; it is a lookup, not
// an invocation, and it is the negative that a retired generation cannot be reached through.
bool hasNativeOverride(Core &core, psx::cpu::ImageIdentity image, std::uint32_t address);

} // namespace vagrant::dynarec
