#pragma once

#include "image_identity.h"

class Core;

namespace vagrant {

// The registry of IMAGE-SCOPED native leaves this title owns for the resident generation.
//
// psxport calls `GameRuntime::registerOverrides` during product boot, which is BEFORE any image
// exists, so an address cannot be resolved to an image identity there. This registry is therefore
// entered from the resident publication boundary instead — the one moment the generation being
// registered is known and current. Overlays get their own boundary when the natural CD queue
// publishes them; a leaf that is not in this table is not owned.
//
// An install refusal is a measured outcome, not a fatal error: a missing leaf is a missing
// measurement, and the run-end census names the refusal. A *partially* installed table would be a
// different thing, so the registry is all-or-nothing and reports which registration failed.
struct NativeOwnerRegistration {
  std::uint32_t attempts = 0;
  std::uint32_t installed = 0;
  std::uint32_t refused = 0;
  const char *refusedOwner = "";

  [[nodiscard]] explicit operator bool() const {
    return refused == 0u;
  }
};

// `residentImage` is the identity the resident load just published. It is required rather than
// optional so a caller cannot register leaves against an image this Core has not published.
NativeOwnerRegistration installResidentNativeOwners(Core &core, psx::cpu::ImageIdentity residentImage);

} // namespace vagrant
