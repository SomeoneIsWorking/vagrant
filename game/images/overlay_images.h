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

// One overlay residency owner per Core; a load replaces the previous image in its slot only after identity checks.
class OverlayImages {
public:
  explicit OverlayImages(Core &core);
  OverlayImages(Core &core, std::array<OverlaySpec, 3> specs);
  OverlayImages(const OverlayImages &) = delete;
  OverlayImages &operator=(const OverlayImages &) = delete;

  // The shipping spec table, public so tests read the ranges.
  const std::array<OverlaySpec, 3> &specs() const {
    return specs_;
  }

  OverlayLoadResult load(OverlayKind kind, std::span<const std::uint8_t> bytes);
  // Publishes a completed whole-sector CD transfer; bytes past the ISO file length are written to RAM but are not part
  // of the image identity.
  OverlayLoadResult loadTransfer(OverlayKind kind, std::span<const std::uint8_t> sectors);
  // Admits bytes already delivered to the slot; the caller proves the transfer completed.
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
