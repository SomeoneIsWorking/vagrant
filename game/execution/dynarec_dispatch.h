#pragma once

#include "execution_exit.h"
#include "image_identity.h"
#include "native_dispatch.h"

#include <cstdint>
#include <string_view>

class Core;

namespace vagrant::dynarec {

// The title's adapter over psxport's per-Core dynarec executor; the only module that spells a budget, resolves an image
// identity or picks a dispatch form. Every path is the Lightrec executor; an unavailable backend is a named failure.

using Override = psx::cpu::NativeFunction;

// Installs a native leaf against the generation that owns `address`; refuses by name when no single image owns it.
bool installNativeOverride(Core &core,
                           std::uint32_t address,
                           std::string_view name,
                           Override function,
                           psx::cpu::ImageIdentity expectedImage = {});

// One finite guest call, resumed until it returns.
psx::cpu::ExecutionResult callGuest(Core &core, std::uint32_t address);

// Finite guest calls with 0-4 arguments set by the caller, yielding `$v0`.
std::uint32_t callReturning0(Core &core, std::uint32_t address);
std::uint32_t callReturning1(Core &core, std::uint32_t address, std::uint32_t a0);
std::uint32_t callReturning2(Core &core, std::uint32_t address, std::uint32_t a0, std::uint32_t a1);
std::uint32_t callReturning4(
    Core &core, std::uint32_t address, std::uint32_t a0, std::uint32_t a1, std::uint32_t a2, std::uint32_t a3);

// One bounded guest turn that may end in any typed exit.
psx::cpu::ExecutionResult executeTurn(Core &core, std::uint32_t address);

// Re-enters the guest body from a native owner, suppressing only `key` for that call.
psx::cpu::ExecutionResult callOriginal(Core &core, psx::cpu::NativeKey key);
psx::cpu::ExecutionResult callOriginal(Core &core, std::uint32_t address);

// Runs the original body at `address` and terminates naming the owner if it does not return within the turn.
void callOriginalToReturn(Core &core, std::uint32_t address, std::string_view owner);

// Terminates when a leaf declared finite did not return.
void requireGuestReturn(const psx::cpu::ExecutionResult &result, std::string_view owner);

// True when `address` is an installed leaf's entry in the generation that owns it now.
bool hasNativeOverride(Core &core, psx::cpu::ImageIdentity image, std::uint32_t address);

// Re-enters the original body of `key`, resuming across turns until it stops exiting on budget; returns the exit reason
// and PC otherwise.
psx::cpu::ExecutionResult callOriginalResuming(Core &core, psx::cpu::NativeKey key);

// A finite leaf needing more than one turn, resumed up to `turnCap` display fields.
// The return address is `r[31]` read before the call because the body overwrites it.
std::uint32_t callGuestResumingToReturn(Core &core, std::uint32_t entry, std::uint32_t turnCap);

} // namespace vagrant::dynarec
