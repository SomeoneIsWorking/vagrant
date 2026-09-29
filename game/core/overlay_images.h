#pragma once

#include "image_identity.h"

#include <array>
#include <cstddef>
#include <cstdint>
#include <optional>
#include <span>
#include <string>

class Core;

namespace vagrant {

enum class OverlayKind : std::uint8_t { Title, Battle, InitBattle };

struct OverlaySpec {
  OverlayKind kind;
  std::string name;
  std::uint32_t guestBase;
  std::size_t byteCount;
  std::string sha256;
};

struct OverlayLoadResult {
  std::optional<psx::cpu::ImageIdentity> identity;
  std::string detail;

  explicit operator bool() const {
    return identity.has_value();
  }
};

// Each Core has one overlay residency owner. A load replaces the previous image in its
// measured address slot only after the complete input has passed title identity checks.
class OverlayImages {
public:
  explicit OverlayImages(Core &core);
  OverlayImages(Core &core, std::array<OverlaySpec, 3> specs);
  OverlayImages(const OverlayImages &) = delete;
  OverlayImages &operator=(const OverlayImages &) = delete;

  // The measured spec table this Core writes into. Public and narrow so a test can ask the
  // SHIPPING values which guest range each module occupies, rather than restating three addresses
  // beside the code that uses them — a restated table is a second answer to "where does this module
  // land", and it is exactly the kind of copy that survives a change to the real one.
  const std::array<OverlaySpec, 3> &specs() const {
    return specs_;
  }

  OverlayLoadResult load(OverlayKind kind, std::span<const std::uint8_t> bytes);
  // Publish a completed whole-sector CD transfer. The final sector's bytes beyond the ISO file
  // length are part of the guest RAM write, but not of the executable image identity.
  OverlayLoadResult loadTransfer(OverlayKind kind, std::span<const std::uint8_t> sectors);
  // Admit bytes already delivered to the measured guest RAM slot by a completed CD transfer.
  // The caller owns proof that the guest queue reached its successful completion state.
  OverlayLoadResult adoptTransfer(OverlayKind kind);

private:
  const OverlaySpec *specFor(OverlayKind kind) const;
  OverlayLoadResult publishTransfer(OverlayKind kind, std::span<const std::uint8_t> sectors, bool alreadyResident);
  OverlayLoadResult publish(OverlayKind kind,
                            std::span<const std::uint8_t> imageBytes,
                            std::span<const std::uint8_t> sectorTail,
                            bool alreadyResident);

  Core &core_;
  std::array<OverlaySpec, 3> specs_;
  std::array<std::optional<psx::cpu::ImageIdentity>, 2> active_{};
};

} // namespace vagrant
