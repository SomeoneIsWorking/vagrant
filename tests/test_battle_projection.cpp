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
constexpr std::int32_t kPresenterCentreY = 112;
constexpr std::int32_t kRetailScreenDistance = 256;
// The test double described at `Fixture`: the smallest finite body, `jr $ra` and its delay slot.
constexpr std::uint32_t kReturnNow = 0x03E00008u;
constexpr std::uint32_t kDelaySlot = 0x00000000u;

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
      // A TEST DOUBLE for the two env leaves, and stated as one: the display-area owner RUNS THE
      // ORIGINAL GUEST BODY and then reads the word the leaf filled, so it needs a body to run.
      // There is no game image here, and the real 14-word body is not a fixture this repository may
      // carry. What is staged is the smallest finite body that RETURNS — `jr $ra` and a delay slot —
      // and the four halfwords the reader checks are staged by the test below, not produced here.
      // So this double establishes that the original ran and the read happened afterwards; it does
      // not assert what retail's leaf writes, which is the byte measurement's claim instead.
      for (std::uint32_t leaf : {facts::kSetDefDispEnv, facts::kSetDefDrawEnv}) {
        core.mem_w32(leaf, kReturnNow);
        core.mem_w32(leaf + 4, kDelaySlot);
      }
    }
  }
};

// The two GTE leaves are PERFORMED by the owner, so the fixture states only the arguments and the
// assertions below read back the coprocessor and the port's own record. No value is written into the
// GTE by hand, because a hand-written register would make the owner's read-back untestable — and,
// more to the point, a pre-seeded register would pass even if the override never did the work,
// which is the defect this test exists to catch.
void stateCentre(Core &core, std::int32_t ofx, std::int32_t ofy) {
  core.r[4] = static_cast<std::uint32_t>(ofx);
  core.r[5] = static_cast<std::uint32_t>(ofy);
}

void stateScreenDistance(Core &core, std::int32_t h) {
  core.r[4] = static_cast<std::uint32_t>(h);
}

// The display-area publication: the caller's `$a0` and `$a3`, plus what the leaf stores at +4/+6 of
// the struct it was handed. The struct is the resident's own `vs_main_dispEnv` — the boot's
// publication — so this fixture drives the publication the first run actually reached.
void stateDisplayArea(Core &core, std::int32_t width, std::int32_t height) {
  core.r[4] = facts::kResidentDispEnv;
  core.r[7] = static_cast<std::uint32_t>(width);
  core.mem_w16(facts::kResidentDispEnv + facts::kLeafEnvWidthOffset, static_cast<std::uint16_t>(width));
  core.mem_w16(facts::kResidentDispEnv + facts::kLeafEnvHeightOffset, static_cast<std::uint16_t>(height));
}

// Drive the INSTALLED override body, not a copy of it. `NativeDispatcher::invoke` is the same entry
// the guest dispatch path uses, so a change to the owner is exercised here without being restated.
//
// The image identity is CHECKED, not assumed: the three `run*` drivers below all need one, and
// `bugprone-unchecked-optional-access` is right that dereferencing it unchecked is a latent
// undefined read. The check names the leaf, because "the fixture did not activate an image" and
// "the wrong leaf did not resolve" are different failures and a reader should be able to tell them
// apart from the abort.
void invokeLeaf(Core &core, std::uint32_t leaf, const char *what) {
  const auto image = core.currentImageIdentity(leaf);
  if (!image) {
    std::fprintf(stderr, "FAIL [%s] 0x%08X resolves to no active image, so no override ran\n", what, leaf);
    std::exit(1);
  }
  (void)core.nativeDispatcher().invoke({*image, leaf});
}

void runCentre(Fixture &fixture) {
  stateCentre(fixture.core, kRetailCentreX, kPresenterCentreY);
  invokeLeaf(fixture.core, facts::kSetGeomOffset, "centre");
}

void runScreenDistance(Fixture &fixture) {
  stateScreenDistance(fixture.core, kRetailScreenDistance);
  invokeLeaf(fixture.core, facts::kSetGeomScreen, "screen distance");
}

void runDisplayArea(Fixture &fixture) {
  stateDisplayArea(fixture.core, kRetailWidth, kRetailHeight);
  invokeLeaf(fixture.core, facts::kSetDefDispEnv, "display area");
}

vagrant::BattleProjectionPublication measure() {
  Fixture fixture;
  expect(vagrant::installBattleProjection(fixture.core, fixture.resident),
         "installing the four measured leaves on a Core that published the resident image must succeed");
  runCentre(fixture);
  runScreenDistance(fixture);
  runDisplayArea(fixture);
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
  return {kRetailCentreX, kPresenterCentreY, kRetailScreenDistance, kRetailWidth, kRetailHeight};
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

// The display-area cross-check, refused on the SHIPPING READER. Same positive control as 7b — the
// stated width is 320 and the height 224, and only the word the leaf stored is perturbed, to the
// 256 that BATTLE's own `screen` rect literal uses — so a reader that ignored the word entirely
// would survive this and fail 7b.
void refusesDrawAreaDisagreement() {
  Fixture fixture;
  if (!vagrant::installBattleProjection(fixture.core, fixture.resident)) {
    return;
  }
  stateDisplayArea(fixture.core, kRetailWidth, kRetailHeight);
  fixture.core.mem_w16(facts::kResidentDispEnv + facts::kLeafEnvWidthOffset,
                       static_cast<std::uint16_t>(facts::kPublicationScreenWidth));
  invokeLeaf(fixture.core, facts::kSetDefDispEnv, "display-area disagreement");
}

// The same reader, handed a struct outside guest RAM. The word address is now DERIVED from the
// caller's `$a0`, so this is a bound the reader owes and the old constant-address version could not
// have needed.
void refusesNonGuestRamArea() {
  Fixture fixture;
  if (!vagrant::installBattleProjection(fixture.core, fixture.resident)) {
    return;
  }
  fixture.core.r[4] = 0x80200000u;
  fixture.core.r[7] = static_cast<std::uint32_t>(kRetailWidth);
  invokeLeaf(fixture.core, facts::kSetDefDispEnv, "display area outside guest RAM");
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
  expect(diesOnSignal(refusesDrawAreaDisagreement),
         "a publication whose own width word disagrees with the stated width must be refused");
  expect(diesOnSignal(refusesNonGuestRamArea), "a display area outside guest RAM must be refused rather than read");

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
         "the overlay viewport rectangle must be readable guest RAM");
  expect(vagrant::BattleProjectionOwner::isGuestRam(facts::kProjectionDistanceWord),
         "the resident projection-distance word must be readable guest RAM");
  expect(!vagrant::BattleProjectionOwner::isGuestRam(0u), "a NULL address is never a valid record");
  expect(!vagrant::BattleProjectionOwner::isGuestRam(0x80200000u), "the first address past main RAM is not a record");
  expect(vagrant::BattleProjectionOwner::isGuestRam(0x80100000u),
         "an address inside the two megabytes of main RAM is a record");
  expect(vagrant::BattleProjectionOwner::isGuestRam(facts::kResidentDispEnv + facts::kLeafEnvWidthOffset),
         "the resident publication's own width word must be readable guest RAM");

  // 7b. THE FIX, AS A POSITIVE TEST OF THE THING THAT WAS BROKEN. The first authenticated run
  //     aborted comparing the boot's 320-wide publication against BATTLE's rectangle, which is
  //     still zero BSS while the resident runs. So the same publication is driven again with that
  //     rectangle left at zero — and the owner must SURVIVE it, which it could not before. The
  //     widths below are the boot's own: they are read out of `_initScreen` at
  //     0x80042054 and the single call site at 0x800420F0, so this is the boot and not a convenient
  //     number.
  {
    Fixture boot;
    expect(vagrant::installBattleProjection(boot.core, boot.resident),
           "the projection owner must install on the fixture that replays the boot publication");
    expect(boot.core.mem_r16s(facts::kViewportWidthWord) == 0,
           "the overlay rectangle must be left at zero in this fixture, or it proves nothing");
    runCentre(boot);
    runScreenDistance(boot);
    runDisplayArea(boot);
    const auto &owner = vagrant::BattleProjectionOwner::from(boot.core);
    expect(owner.retail().drawWidth == 320 && owner.retail().drawHeight == 224,
           "the boot's 320x224 publication must be measured while the overlay rectangle holds zero");
    expect(boot.core.mem_r16s(facts::kViewportWidthWord) == 0,
           "reading the publication must not have written the overlay rectangle");
  }

  // 7c. THE REFUSAL IS STILL A REFUSAL, observed in the refusals section below as
  //     `refusesDrawAreaDisagreement`. A cross-check that stopped disagreeing is a cross-check that
  //     stopped checking, so the negative case has to be on the shipping reader: the guest states
  //     320 and the word the leaf stored is 256. The BATTLE publication installs exactly that pair —
  //     its `screen` rect literal is 256 — so this is a value the title really does produce.

  // 7d. THE OWNER PERFORMS THE GTE LEAVES RATHER THAN OBSERVING A FIELD NOBODY WROTE. Before this
  //     change the four overrides REPLACED all four resident leaves, so the guest's GTE geometry and
  //     its display area were never written by anything; a pre-seeded register would have hidden
  //     that, so the fixture seeds NOTHING and the assertion reads both destinations back. This is
  //     the test that would have failed against the previous owner.
  {
    Fixture gte;
    expect(vagrant::installBattleProjection(gte.core, gte.resident),
           "the GTE fixture must install the same four leaves");
    // The centre leaf alone, so the argument-register assertion below is not confused by the screen
    // distance leaf that shares `$a0` and legitimately leaves it unshifted.
    runCentre(gte);
    expect(gte_read_ctrl(facts::kGteControlOfx) == (static_cast<std::uint32_t>(kRetailCentreX) << 16),
           "SetGeomOffset must have moved CR24 itself, not merely recorded an argument");
    expect(gte_read_ctrl(facts::kGteControlOfy) == (static_cast<std::uint32_t>(kPresenterCentreY) << 16),
           "SetGeomOffset must have moved CR25 itself");
    expect(gte.core.rsub.projParams.geomOfx() == static_cast<float>(kRetailCentreX) &&
               gte.core.rsub.projParams.geomOfy() == static_cast<float>(kPresenterCentreY),
           "the port's own projection record must move with the coprocessor, which is what makes the "
           "centre cross-check two statements rather than one");
    // And the leaf's own side effect on its argument registers, read from the leaf's two `sll`
    // words at 0x80041540. A widening is only idempotent if the owner never leaves a shifted value
    // where retail left an unshifted one.
    expect(gte.core.r[4] == (static_cast<std::uint32_t>(kRetailCentreX) << 16) &&
               gte.core.r[5] == (static_cast<std::uint32_t>(kPresenterCentreY) << 16),
           "SetGeomOffset must leave its arguments shifted into place, as its own body does");
    runScreenDistance(gte);
    expect(gte_read_ctrl(facts::kGteControlH) == static_cast<std::uint32_t>(kRetailScreenDistance),
           "SetGeomScreen must have moved CR26 itself");
    expect(gte.core.rsub.projParams.geomH() == static_cast<float>(kRetailScreenDistance),
           "SetGeomScreen must move the port's own record of H with the coprocessor");
    expect(gte.core.r[4] == static_cast<std::uint32_t>(kRetailScreenDistance),
           "SetGeomScreen must leave its argument unshifted: its body is one register move and no "
           "shift, so an owner that shifted it would be substituting behaviour");
  }

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
  std::printf("battle projection contract: retail publication %dx%d at (%d,%d) H %d measured; the GTE "
              "leaves moved CR24/CR25/CR26 themselves; 4:3 identity and the 428 px 16:9 derivation both "
              "accepted; 6 derivation, 2 display-area and 2 registration refusals observed to fire\n",
              publication.drawWidth,
              publication.drawHeight,
              publication.centreX,
              publication.centreY,
              publication.screenDistance);
  return 0;
}
