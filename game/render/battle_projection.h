// BattleProjectionOwner — Vagrant Story's own guest projection publication, and the refusal that
// keeps a widening from being claimed on a reconstruction.
//
// WHAT THE GUEST'S PROJECTION IS, AND WHERE IT IS PUBLISHED. Two independent sources agree: this
// repository's byte measurement (`tools/re_frame.py` against the authenticated SLUS_010.40
// executable, recorded in `docs/battle-rendering.md`) and the vendored CC0 decompilation's own
// per-module symbol map. The publication is BATTLE.PRG's `func_800760CC` at 0x800760CC — an OVERLAY
// address, in a module loaded at 0x80068800, not in the boot executable — and it states its
// viewport through four RESIDENT SDK leaves: SetGeomOffset, SetGeomScreen, SetDefDrawEnv and
// SetDefDispEnv. `tools/re_projection.py` re-derives that agreement and fails when it stops holding.
//
// WHY THE OWNER SITS ON THE LEAVES AND NOT ON THE OVERLAY CALL SITE. BATTLE's field presenter
// re-states a LITERAL horizontal centre through SetGeomOffset on every single field, so an owner on
// the overlay's viewport call would be overwritten 60 times a second. The resident leaf is one
// address in one image, every caller's centre passes through it, and the leaf's argument is the
// title's own value at that instant — never a value this owner wrote — which is what makes a
// widening idempotent by construction instead of by a guard against accumulation.
//
// WHY IT REFUSES INSTEAD OF WIDENING. There is no authenticated image on this machine, so not one
// instruction word of the four leaves has been read here, and the bodies are a reconstruction. Worse,
// a centre-only widening would be wrong even if they had: the horizontal CLIP is published by the
// same overlay call with a VRAM side-by-side layout and a screen rectangle that the reconstruction
// reports as 256 against a 320-wide display area. Moving the centre without moving the clip crops
// the left of every field instead of widening anything, so this owner measures the publication,
// derives the widening, and refuses to apply it. `derive()` is the shipped arithmetic a future clip
// owner will call; the refusals inside it are the tests.
#pragma once

#include "battle_projection_facts.h"
#include "guest_widescreen_projection.h"
#include "image_identity.h"

#include <cstdint>
#include <string_view>

class Core;

namespace vagrant {

// What the guest STATED about its viewport, read back from three independent places on every call:
// the framework's record of the values the SDK leaves were handed, the GTE control registers those
// leaves wrote, and the guest's own resident viewport rectangle. Nothing here is remembered — every
// field is re-read — because the title re-authors its viewport per field.
struct BattleProjectionPublication {
  int centreX = 0;        // CR24 / ProjParams::geomOfx, the horizontal centre
  int centreY = 0;        // CR25 / geomOfy. Recorded, never asserted: the two publication sites
                          // disagree about it (the overlay's is height-derived and the presenter's
                          // is a literal), so a single expected value would be a guess.
  int screenDistance = 0; // CR26 / geomH, the GTE projection-plane distance H
  int drawWidth = 0;      // the width the title passed to its draw area, cross-checked against the
                          // guest's own rectangle
  int drawHeight = 0;     // the height from the guest's own rectangle

  [[nodiscard]] bool valid() const {
    return centreX > 0 && centreY > 0 && screenDistance > 0 && drawWidth > 0 && drawHeight > 0;
  }
};

// A wide publication derived from a MEASURED retail one and the framework's plan. `widens` is false
// for the 4:3 identity, which is produced by construction rather than by a branch: the plan's margin
// is zero there, so the retail values pass through untouched.
struct WideBattleProjection {
  int centreX = 0;
  int drawWidth = 0;
  int clipRight = 0;
  bool widens = false;
};

class BattleProjectionOwner {
public:
  // --- the three installed override bodies, one per publication leaf --------------------------
  //
  // Each runs the retail body FIRST and observes afterwards, so an observer can never change what
  // the guest published: this owner is a measurement, and its refusals are about the measurement
  // disagreeing with itself, never about substituting a value.
  void observeCentre(Core &core);
  void observeScreenDistance(Core &core);
  void observeDrawArea(Core &core);

  [[nodiscard]] const BattleProjectionPublication &retail() const {
    return retail_;
  }
  // True once all three leaves have been observed at least once, which is the only state in which
  // `retail()` is a whole publication rather than a partial one.
  [[nodiscard]] bool observed() const {
    return centreSet_ && screenDistanceSet_ && drawAreaSet_;
  }

  // PURE. The wide publication a plan asks for, derived only from the MEASURED retail publication.
  // Refuses — aborts naming the cause — on the two conditions under which a "widening" would not be
  // one, because a wrong picture published under a wide claim is worse than no widening:
  //   * a retail centre that is not the half-width the publication itself states, so moving the
  //     centre to the plan's would be a translation rather than a widening; and
  //   * a plan whose clip is not widened in lockstep with its projection, so the newly visible
  //     geometry would fall outside the guest's own clip and the field would be cropped.
  static WideBattleProjection derive(const BattleProjectionPublication &retail, const GuestProjectionPlan &plan);

  // Is this a guest RAM address the owner may read? Public and pure because that bound is exactly
  // the kind of thing a fixture using only low addresses cannot catch for itself.
  static bool isGuestRam(std::uint32_t address);

  // This title's owner on a running Core. The checked downcast lives here so no other file repeats
  // the rule "the per-Core measurement belongs to the owner on this Core's context", and so a Core
  // running another title's policy is a named refusal instead of a silent no-op.
  static BattleProjectionOwner &from(Core &core);

private:
  BattleProjectionPublication retail_{};
  bool centreSet_{};
  bool screenDistanceSet_{};
  bool drawAreaSet_{};
};

// Install this title's four measured publication leaves on one Core, keyed by the image identity
// the resident load just published. NOT reachable through the framework's stock library-service
// table: these addresses are this title's, and each is refused unless it resolves inside the image
// this Core actually published — an address alone does not identify PSX code, because the overlays
// reuse 0x80068800. Returns false, and changes nothing, when any leaf does not resolve; the caller
// decides whether an unowned projection is fatal.
bool installBattleProjection(Core &core, psx::cpu::ImageIdentity residentImage);

} // namespace vagrant
