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

  OverlayLoadResult load(OverlayKind kind, std::span<const std::uint8_t> bytes);

private:
  Core &core_;
  std::array<OverlaySpec, 3> specs_;
  std::array<std::optional<psx::cpu::ImageIdentity>, 2> active_{};
};

} // namespace vagrant
