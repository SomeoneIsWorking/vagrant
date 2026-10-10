// Owns Vagrant Story's projection publication, observed through four resident SDK leaves. It sits on the leaves, not
// BATTLE's call site, because the presenter restates a literal centre through SetGeomOffset every field.
#pragma once

#include "image_identity.h"
#include "render/battle_projection_facts.h"

#include <cstdint>

class Core;

namespace vagrant {

// What the guest stated about its viewport, read back per call; the title re-authors it per field.
struct BattleProjectionPublication {
  int centreX = 0;        // CR24 / ProjParams::geomOfx, the horizontal centre
  int centreY = 0;        // CR25 / geomOfy; the overlay and the presenter state different values
  int screenDistance = 0; // CR26 / geomH, the GTE projection-plane distance H
  int drawWidth = 0;      // the width the title passed to its draw area
  int drawHeight = 0;     // the height from the guest's own rectangle

  [[nodiscard]] bool valid() const {
    return centreX > 0 && centreY > 0 && screenDistance > 0 && drawWidth > 0 && drawHeight > 0;
  }
};

// What one display-area publication left in the struct the leaf was handed: width at +4, height at +6.
struct PublishedArea {
  int width = 0;
  int height = 0;
};

// The two statements the display-area cross-check compares, as one value so they cannot be swapped.
struct DisplayAreaPublication {
  std::uint32_t env = 0;        // the caller's `$a0`: the struct the leaf was handed
  std::int32_t statedWidth = 0; // the caller's `$a3`: the width the guest stated
};

class BattleProjectionOwner {
public:
  // GeomOffset moves two GTE registers and nothing else, so it is performed then observed.
  void publishCentre(Core &core);
  void publishScreenDistance(Core &core);
  void publishDisplayArea(Core &core, std::uint32_t leaf);

  // The reading, separate from publishing so a test can drive it; refuses when the two statements of one horizontal
  // extent disagree or the address is outside guest RAM.
  [[nodiscard]] static PublishedArea readPublishedArea(Core &core, const DisplayAreaPublication &stated);

  [[nodiscard]] const BattleProjectionPublication &retail() const {
    return retail_;
  }
  // True once all three leaves have been observed, the only state in which `retail()` is whole.
  [[nodiscard]] bool observed() const {
    return centreSet_ && screenDistanceSet_ && drawAreaSet_;
  }

  // Is this a guest RAM address the owner may read?
  static bool isGuestRam(std::uint32_t address);

  // The owner on a running Core; refuses a read before the guest has stated a complete viewport.
  static BattleProjectionOwner &from(Core &core);

private:
  // Takes the stated value: the GTE leaves leave their arguments shifted in the register.
  void recordCentre(Core &core, std::int32_t statedX, std::int32_t statedY);
  void recordScreenDistance(Core &core, std::int32_t statedH);

  BattleProjectionPublication retail_{};
  bool centreSet_{};
  bool screenDistanceSet_{};
  bool drawAreaSet_{};
};

// Installs the four leaves keyed by the image identity the resident load published; each address is
// refused unless it resolves inside that image, because overlays reuse 0x80068800.
bool installBattleProjection(Core &core, psx::cpu::ImageIdentity residentImage);

} // namespace vagrant
