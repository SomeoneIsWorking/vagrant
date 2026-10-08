#pragma once

#include "image_identity.h"

class Core;

namespace vagrant {

// Image-scoped native leaves for the resident generation.
// `registerOverrides` runs before any image exists, so registration is entered from the publication boundary. The table
// is all-or-nothing and reports which registration was refused.
struct NativeOwnerRegistration {
  std::uint32_t attempts = 0;
  std::uint32_t installed = 0;
  std::uint32_t refused = 0;
  const char *refusedOwner = "";

  [[nodiscard]] explicit operator bool() const {
    return refused == 0u;
  }
};

// Required so leaves cannot be registered against an image this Core has not published.
NativeOwnerRegistration installResidentNativeOwners(Core &core, psx::cpu::ImageIdentity residentImage);

} // namespace vagrant
