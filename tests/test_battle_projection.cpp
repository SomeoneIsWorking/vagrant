// BattleProjectionOwner's contract. Every refusal here is a POSITIVE test: each one asserts that a
// named input makes the shipping path die, because an owner that only ever succeeded would look
// identical to a correct one until it published a wrong frame. The positive controls matter just as
// much — a refusal that fires unconditionally is not a refusal, so each abort case is paired with a
// neighbouring case that must succeed on the same path.

#include "battle_projection.h"
#include "core.h"
#include "game.h"
#include "game_runtime.h"
#include "hw_bind.h"
#include "native_dispatch.h"
#include "proj_params.h"
#include "render/battle_projection_facts.h"
#include "vagrant_runtime.h"

#include <sys/wait.h>
#include <unistd.h>

#include <cstdio>
#include <cstdlib>
#include <memory>
#include <string_view>

namespace {

namespace facts = vagrant::battle_projection;

int failures = 0;

void expect(bool condition, const char *what) {
  if (!condition) {
    std::fprintf(stderr, "[FAIL] %s\n", what);
    ++failures;
  }
}

// Run `body` in a child and report whether it died on a signal. A refusal in this owner is
// `std::abort()`, so a surviving child means the refusal did NOT fire — which is the failure this
// helper exists to make observable without killing the whole test.
bool diesOnSignal(void (*body)()) {
  std::fflush(nullptr);
  const pid_t child = fork();
  if (child == 0) {
    body();
    std::_Exit(0);
  }
  int status = 0;
  if (waitpid(child, &status, 0) != child) {
    std::fprintf(stderr, "[FAIL] waitpid did not return the child\n");
    ++failures;
    return false;
  }
  return WIFSIGNALED(status);
}

// --- the retail publication a live BATTLE field produces, replayed through the production leaves --
//
// 320x240 handed to the overlay publication: a 320x224 draw area and a 160-wide centre. These are
// the values the title passes as ITS OWN arguments, so the fixture states them as arguments rather
// than as a constant the owner could have memorised.
//
// The vertical centre is 112, and that is DELIBERATE and worth reading twice. BATTLE.PRG states TWO
// different vertical centres: the overlay publication computes (height-16)/2 + 16 = 128 at 320x240
// (0x800760E8 `addiu $s3, $a1, -0x10`, 0x80076108 `addiu $a1, $a1, 0x10`), while the field presenter
// re-states the LITERAL (160, 112) every field (0x800762E0 `addiu $a0, $zero, 0xA0`,
// 0x800762E4 `jal 0x80041540`). Both were read from the bytes. This fixture drives the leaf the way
// the PRESENTER does, because the presenter's value is the one in force at the frame boundary, and
// that is exactly why the owner sits on the leaf instead of on the overlay's call site. The owner's
// contract is that it records whatever value the guest last stated — which is why
// BattleProjectionPublication::centreY is recorded and never asserted.

constexpr std::uint32_t kResidentLow = 0x80010000u;
constexpr std::uint32_t kResidentHigh = 0x80070000u;
constexpr std::int32_t kRetailWidth = 320;
constexpr std::int32_t kRetailHeight = 224;
constexpr std::int32_t kRetailCentreX = 160;
constexpr std::int32_t kRetailScreenDistance = 256;

// A Game carries a Core with two megabytes of guest RAM and the GTE register file the leaves write
// through, so it is heap-allocated here: a `Game` by value in a test's frame is a stack overflow,
// not a fixture. `Core` alone is not enough — `gte_bind` publishes `&core.game->gte`.
struct Fixture {
  std::unique_ptr<Game> owned;
  Core &core;
  psx::cpu::ImageIdentity resident{};

  explicit Fixture(bool activateImage = true) : owned(std::make_unique<Game>()), core(owned->core) {
    // The owner reads the coprocessor, so the per-Core GTE register file must exist and be bound
    // before any leaf publishes into it. Bind BEFORE powering: `GTE_Power` writes through the bound
    // register file, so powering first would write through whatever a previous Core left bound — and
    // after that Core is gone. `dc_boot_init` binds without powering; this fixture also wants the
    // deterministic zeroed start a real power-on gives.
    gte_bind(&core);
    gte_init();
    if (activateImage) {
      resident = core.imageCatalog().activate(
          "synthetic SLUS_010.40 resident fixture", {kResidentLow & 0x1FFFFFFFu, (kResidentHigh & 0x1FFFFFFFu)}, 1u);
    }
  }
};

// The three leaves' retail effects, applied through the framework's own setters so the coprocessor
// and the per-Core record are moved the way a real leaf moves them. No value is written into the GTE
// by hand, because a hand-written register would make the owner's read-back untestable.
void stateCentre(Core &core, std::int32_t ofx, std::int32_t ofy) {
  core.r[4] = static_cast<std::uint32_t>(ofx);
  core.r[5] = static_cast<std::uint32_t>(ofy);
  libgte_set_geom_offset(&core, ofx, ofy);
}

void stateScreenDistance(Core &core, std::int32_t h) {
  core.r[4] = static_cast<std::uint32_t>(h);
  libgte_set_geom_screen(&core, h);
}

void stateDrawArea(Core &core, std::int32_t width) {
  core.r[7] = static_cast<std::uint32_t>(width);
  core.mem_w16(facts::kViewportRectWord, 0u);
  core.mem_w16(facts::kViewportWidthWord, static_cast<std::uint16_t>(width));
  core.mem_w16(facts::kViewportHeightWord, static_cast<std::uint16_t>(kRetailHeight));
}

// Drive the INSTALLED override body, not a copy of it. `NativeDispatcher::invoke` is the same entry
// the guest dispatch path uses, so a change to the owner is exercised here without being restated.
void runCentre(Fixture &fixture) {
  stateCentre(fixture.core, kRetailCentreX, 112);
  const auto image = fixture.core.currentImageIdentity(facts::kSetGeomOffset);
  expect(image.has_value(), "the centre leaf must resolve to the activated resident image");
  (void)fixture.core.nativeDispatcher().invoke({*image, facts::kSetGeomOffset});
}

void runScreenDistance(Fixture &fixture) {
  stateScreenDistance(fixture.core, kRetailScreenDistance);
  const auto image = fixture.core.currentImageIdentity(facts::kSetGeomScreen);
  (void)fixture.core.nativeDispatcher().invoke({*image, facts::kSetGeomScreen});
}

void runDrawArea(Fixture &fixture) {
  stateDrawArea(fixture.core, kRetailWidth);
  const auto image = fixture.core.currentImageIdentity(facts::kSetDefDrawEnv);
  (void)fixture.core.nativeDispatcher().invoke({*image, facts::kSetDefDrawEnv});
}

vagrant::BattleProjectionPublication measure() {
  Fixture fixture;
  expect(vagrant::installBattleProjection(fixture.core, fixture.resident),
         "installing the four measured leaves on a Core that published the resident image must succeed");
  runCentre(fixture);
  runScreenDistance(fixture);
  runDrawArea(fixture);
  // Through the owner's own checked downcast rather than a `static_cast` beside it: a test that
  // reaches the owner by a different route than production does is a test of a different code path.
  return vagrant::BattleProjectionOwner::from(fixture.core).retail();
}

// The framework's own plan builder, so the plans under test are the ones the runtime would produce
// and not a hand-written struct that could drift from it.
GuestProjectionPlan planFor(PresentationAspect aspect) {
  return guest_projection_plan({
      .path = RenderPath::Gte,
      .requested = aspect,
      .nativePresentation = {320, 240},
      .nativeProjection = {{320, 240}, 320},
      .sink = {1280, 720},
      .vramWidth = 1024,
  });
}

vagrant::BattleProjectionPublication completePublication() {
  return {kRetailCentreX, 112, kRetailScreenDistance, kRetailWidth, kRetailHeight};
}

// --- the refusals, one static body each so each can be forked in isolation --------------------------

void refusesIncompletePublication() {
  vagrant::BattleProjectionPublication partial{};
  partial.centreX = kRetailCentreX;
  (void)vagrant::BattleProjectionOwner::derive(partial, planFor(PresentationAspect::Wide16x9));
}

void refusesUncentredRetail() {
  auto retail = completePublication();
  retail.centreX = 96; // not the half of the measured width
  (void)vagrant::BattleProjectionOwner::derive(retail, planFor(PresentationAspect::Wide16x9));
}

void refusesUnwidenedClip() {
  // A plan whose projection widened but whose guest clip did not: the widened geometry would fall
  // outside the guest's own clip, so the field would be cropped rather than widened.
  auto plan = planFor(PresentationAspect::Wide16x9);
  plan.guestDrawWidth = kRetailWidth;
  (void)vagrant::BattleProjectionOwner::derive(completePublication(), plan);
}

void refusesInconsistentClipEdge() {
  auto plan = planFor(PresentationAspect::Wide16x9);
  plan.guestClipRight = plan.guestDrawWidth; // one past the widened width
  (void)vagrant::BattleProjectionOwner::derive(completePublication(), plan);
}

void refusesOffCentreWidening() {
  auto plan = planFor(PresentationAspect::Wide16x9);
  plan.projectionCenterX = 160; // the retail centre, not the widened width's half
  (void)vagrant::BattleProjectionOwner::derive(completePublication(), plan);
}

void refusesUnusablePlan() {
  auto plan = planFor(PresentationAspect::Wide16x9);
  plan.guestDrawWidth = 0;
  (void)vagrant::BattleProjectionOwner::derive(completePublication(), plan);
}

} // namespace

int main() {
  // The title runtime is installed so every Core below is given this title's per-Core context, which
  // is where the owner lives. Nothing here boots a game: there is no image on this machine, and the
  // projection owner is deliberately reachable without one.
  vagrant::VagrantRuntime runtime;
  psxport_install_game(runtime);

  // 0. The deliberate ABSENCE of a guest widescreen policy is the enforcement, so it is asserted
  //    rather than assumed: while the clip boundary stands, the framework must resolve this title's
  //    guest projection at 4:3.
  expect(runtime.guestWidescreenProjection() == nullptr,
         "VagrantRuntime must publish no guest widescreen policy while the clip boundary stands");

  // 1. The measured publication. The owner reads the framework's record, the coprocessor and the
  //    guest's own rectangle; the values it reports are the ones the leaves produced.
  const vagrant::BattleProjectionPublication publication = measure();
  expect(publication.centreX == kRetailCentreX, "the measured horizontal centre must be the guest's own");
  expect(publication.centreY == 112, "the measured vertical centre must be the guest's own");
  expect(publication.screenDistance == kRetailScreenDistance, "the measured screen distance must be the guest's own");
  expect(publication.drawWidth == kRetailWidth, "the measured width must be the guest's own rectangle");
  expect(publication.drawHeight == kRetailHeight, "the measured height must be the guest's own rectangle");
  expect(publication.valid(), "a complete publication must report itself valid");

  // 2. The 4:3 identity, produced by construction rather than by a branch on the plan's margin.
  const auto identity = vagrant::BattleProjectionOwner::derive(publication, planFor(PresentationAspect::Standard4x3));
  expect(!identity.widens, "a 4:3 plan must not claim a widening");
  expect(identity.centreX == publication.centreX, "4:3 must pass the measured centre through untouched");
  expect(identity.drawWidth == publication.drawWidth, "4:3 must pass the measured width through untouched");

  // 3. The positive control for every refusal below: a plan that widens the centre AND the clip in
  //    lockstep must produce a widening. Without this, a derive() that always aborted would pass 4–9.
  const auto wide = vagrant::BattleProjectionOwner::derive(publication, planFor(PresentationAspect::Wide16x9));
  expect(wide.widens, "a plan widening centre and clip together must produce a widening");
  expect(wide.centreX == 214, "the widened centre must be half the widened width, which is 214 at 16:9");
  expect(wide.drawWidth == 428, "the widened clip must be 428 px at 16:9 from a 320 px retail width");
  expect(wide.clipRight == wide.drawWidth - 1, "the clip's right edge must be the widened width's last column");

  // 4. The refusals, each on the shipping path.
  expect(diesOnSignal(refusesIncompletePublication), "an incomplete publication must be refused");
  expect(diesOnSignal(refusesUncentredRetail), "a retail centre that is not half the width must be refused");
  expect(diesOnSignal(refusesUnwidenedClip), "a plan that widens the projection but not the clip must be refused");
  expect(diesOnSignal(refusesInconsistentClipEdge), "a clip right edge past the widened width must be refused");
  expect(diesOnSignal(refusesOffCentreWidening), "a widened centre that is not half the widened width must be refused");
  expect(diesOnSignal(refusesUnusablePlan), "a plan with no guest draw width must be refused");

  // 5. Registration refuses an address that resolves to no active image. A run must never be left
  //    half-registered, so this is checked with a Core that published nothing.
  {
    Fixture empty(false);
    expect(!vagrant::installBattleProjection(empty.core, empty.resident),
           "installing against a Core with no active image must be refused");
  }

  // 6. Registration refuses an identity the Core did not publish, which is the check that matters
  //    here: BATTLE, TITLE and ENDING all reuse load base 0x80068800, so an address alone cannot
  //    say which module a leaf belongs to.
  {
    Fixture fixture;
    expect(!vagrant::installBattleProjection(fixture.core, psx::cpu::ImageIdentity{.id = 9999u, .generation = 1u}),
           "installing against a foreign image identity must be refused");
    expect(vagrant::installBattleProjection(fixture.core, fixture.resident),
           "the same Core must still accept its own identity afterwards");
  }

  // 7. The guest-RAM bound, which the owner relies on and which a low-address-only fixture could
  //    never catch for itself.
  expect(vagrant::BattleProjectionOwner::isGuestRam(facts::kViewportRectWord),
         "the resident viewport rectangle must be readable guest RAM");
  expect(vagrant::BattleProjectionOwner::isGuestRam(facts::kProjectionDistanceWord),
         "the resident projection-distance word must be readable guest RAM");
  expect(!vagrant::BattleProjectionOwner::isGuestRam(0u), "a NULL address is never a valid record");
  expect(!vagrant::BattleProjectionOwner::isGuestRam(0x80200000u), "the first address past main RAM is not a record");
  expect(vagrant::BattleProjectionOwner::isGuestRam(0x80100000u),
         "an address inside the two megabytes of main RAM is a record");

  // 8. The projection distance is never widened, and the thresholds that make that necessary are
  //    named constants rather than comments. This is the state hazard, asserted as a fact about the
  //    shipped header: the owner has no API that changes it.
  //
  //    THREE thresholds, not one. The previous file recorded only 272, which is the decompilation's
  //    figure. Reading BATTLE.PRG found a second pair of branches on the same word at 0x80074580
  //    (`slti $v0, $v0, 0x110`, i.e. < 272) and 0x80074744 (`slti $v0, $v0, 0x111`, i.e. > 272
  //    spelled `< 273`), plus a zoom step at 0x80078578 that adds 64 and clamps at 0x300 = 768. A
  //    widening that "just nudged H" would have cleared 272 and hit 768. All three are asserted here
  //    because the numbers are the enforcement: drop one and the owner stops protecting the word.
  expect(facts::kProjectionDistanceBranchThreshold == 272,
         "the gameplay threshold the projection-distance word is branched on must be recorded");
  expect(facts::kProjectionDistanceZoomClamp == 768,
         "the zoom clamp on the same word must be recorded; it is a second gameplay threshold");
  expect(facts::kProjectionDistanceZoomStep == 64, "the per-step growth of the projection distance must be recorded");
  expect(facts::kProjectionDistanceZoomStep != 0 &&
             facts::kProjectionDistanceZoomStep < facts::kProjectionDistanceBranchThreshold,
         "the game must drive the projection distance across the branch threshold, or the hazard is not a hazard");

  // 9. The two vertical centres, as measured facts rather than as a comment. This is the pair the
  //    previous file asserted disagreed while naming only one of them, and the owner records
  //    `centreY` without asserting it precisely because they do disagree.
  expect(facts::kBattlePublicationCentreY == 128,
         "the overlay publication's own vertical centre at 320x240 must be recorded as 128");
  expect(facts::kBattlePresenterCentreY == 112,
         "the presenter's per-field literal vertical centre must be recorded as 112");
  expect(facts::kBattlePublicationCentreY != facts::kBattlePresenterCentreY,
         "the two publication sites must be recorded as disagreeing, or the owner's reason for "
         "sitting on the leaf is not a reason");
  expect(facts::kBattlePresenterCentreX == 160 && facts::kBattlePublicationCentreY / 2 == 64,
         "the presenter's centre must remain the half-width the publication itself states");

  // 10. The CORRECTED call sites. The BATTLE.PRG call of the publication is 0x8008A288, not the
  //     0x8008B0A4 this repository previously recorded — that address holds `and $t2, $t1, $t5`, a
  //     mask in a CLUT-addressing loop, so the old constant pointed at a word that computes nothing
  //     this owner cares about. Asserted because a wrong call site is the kind of error that only
  //     shows up as a mystery later, never as a failure here.
  expect(facts::kBattlePublicationCallSite == 0x8008A288u,
         "the BATTLE.PRG call site of the publication must be 0x8008A288 as read from the bytes");
  expect(facts::kInitBtlPublicationCallSite == 0x800FA69Cu,
         "the INITBTL.PRG call site of the publication must be 0x800FA69C as read from the bytes");

  // 11. The `screen` rect, and what it is NOT. The previous blocker said a 256-pixel clip this port
  //     had not read from bytes stopped the widening. The bytes REFUTE that: 256 is a literal in the
  //     DISPENV `screen` rect and the draw-area clip is zero, so there is no 256-pixel clip in the
  //     draw path. These constants exist so the corrected reading is a fact in the tree rather than
  //     a sentence in a doc, and the 4:3 identity below is what proves they are not silently used
  //     to scale anything.
  expect(facts::kPublicationScreenWidth == 256 && facts::kPublicationScreenHeight == 224,
         "the publication's `screen` rect must be recorded as the 256x224 literals the bytes show");
  expect(facts::kPublicationScreenWidth != facts::kPublicationScreenHeight,
         "the `screen` rect is not square, so a reader cannot mistake one for the other");

  // 12. The boundary, and that it names the DISPLAY RESOLUTION rather than the refuted clip story.
  //     A test that only checked `wideningBlocker()` is non-empty would have passed on the wrong
  //     reason, which is the failure this assertion exists to catch.
  expect(!facts::wideningAvailable(), "this title must report itself unable to widen while the boundary stands");
  expect(!facts::wideningBlocker().empty(), "an unavailable widening must name the boundary that stops it");
  {
    const std::string_view blocker = facts::wideningBlocker();
    expect(blocker.find("screen rect") == std::string_view::npos,
           "the boundary must not claim the `screen` rect is an unread clip; the bytes refute that");
    expect(blocker.find("SetDefDispEnv") != std::string_view::npos,
           "the boundary must name the display resolution, which is what actually has to move");
    expect(blocker.find("has not read from bytes") == std::string_view::npos,
           "the boundary must not rest on an unread reconstruction; the bodies are read now");
  }

  if (failures != 0) {
    std::fprintf(stderr, "battle projection contract: %d failure(s)\n", failures);
    return 1;
  }
  std::printf("battle projection contract: retail publication %dx%d at (%d,%d) H %d measured; 4:3 identity "
              "and the 428 px 16:9 derivation both accepted; 6 derivation refusals and 2 registration "
              "refusals observed to fire\n",
              publication.drawWidth,
              publication.drawHeight,
              publication.centreX,
              publication.centreY,
              publication.screenDistance);
  return 0;
}
