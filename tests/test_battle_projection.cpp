// BattleProjectionOwner contract; each abort case is paired with a neighbouring case that must succeed.

#include "core.h"
#include "game.h"
#include "game_runtime.h"
#include "hw_bind.h"
#include "native_dispatch.h"
#include "proj_params.h"
#include "render/battle_projection.h"
#include "render/battle_projection_facts.h"
#include "runtime/vagrant_runtime.h"

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

// Run `body` in a child and report whether it died on a signal; refusals are `std::abort()`.
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

// Retail publication replayed through the production leaves: 320x240 handed to the overlay publication.
// The vertical centre is 112: the overlay computes (height-16)/2 + 16 = 128 (0x800760E8, 0x80076108), but the
// field presenter re-states (160, 112) every field (0x800762E0, 0x800762E4) and that is the value in force.
// The owner records the last stated centreY and never asserts it.

constexpr std::uint32_t kResidentLow = 0x80010000u;
constexpr std::uint32_t kResidentHigh = 0x80070000u;
constexpr std::int32_t kRetailWidth = 320;
constexpr std::int32_t kRetailHeight = 224;
constexpr std::int32_t kRetailCentreX = 160;
constexpr std::int32_t kPresenterCentreY = 112;
constexpr std::int32_t kRetailScreenDistance = 256;
// Smallest finite body: `jr $ra` and its delay slot.
constexpr std::uint32_t kReturnNow = 0x03E00008u;
constexpr std::uint32_t kDelaySlot = 0x00000000u;

// Heap-allocated: a `Game` by value overflows the stack, and `gte_bind` publishes `&core.game->gte`.
struct Fixture {
  std::unique_ptr<Game> owned;
  Core &core;
  psx::cpu::ImageIdentity resident{};

  explicit Fixture(bool activateImage = true) : owned(std::make_unique<Game>()), core(owned->core) {
    // Bind the GTE before powering: `GTE_Power` writes through the bound register file.
    gte_bind(&core);
    gte_init();
    if (activateImage) {
      resident = core.imageCatalog().activate(
          "synthetic SLUS_010.40 resident fixture", {kResidentLow & 0x1FFFFFFFu, (kResidentHigh & 0x1FFFFFFFu)}, 1u);
      // Test double for the two env leaves: the owner runs the original body and then reads the word it filled,
      // so a minimal `jr $ra` body stands in; the four halfwords are staged by the test.
      for (std::uint32_t leaf : {facts::kSetDefDispEnv, facts::kSetDefDrawEnv}) {
        core.mem_w32(leaf, kReturnNow);
        core.mem_w32(leaf + 4, kDelaySlot);
      }
    }
  }
};

// The owner performs the GTE leaves; nothing is pre-seeded, so a skipped override would show.
void stateCentre(Core &core, std::int32_t ofx, std::int32_t ofy) {
  core.r[4] = static_cast<std::uint32_t>(ofx);
  core.r[5] = static_cast<std::uint32_t>(ofy);
}

void stateScreenDistance(Core &core, std::int32_t h) {
  core.r[4] = static_cast<std::uint32_t>(h);
}

// Display-area publication: caller's `$a0` and `$a3`, plus what the leaf stores at +4/+6 of `vs_main_dispEnv`.
void stateDisplayArea(Core &core, std::int32_t width, std::int32_t height) {
  core.r[4] = facts::kResidentDispEnv;
  core.r[7] = static_cast<std::uint32_t>(width);
  core.mem_w16(facts::kResidentDispEnv + facts::kLeafEnvWidthOffset, static_cast<std::uint16_t>(width));
  core.mem_w16(facts::kResidentDispEnv + facts::kLeafEnvHeightOffset, static_cast<std::uint16_t>(height));
}

// Drive the installed override through `NativeDispatcher::invoke`; the identity check names the leaf.
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
  // Through the owner's checked downcast, as production does.
  return vagrant::BattleProjectionOwner::from(fixture.core).retail();
}

// The framework's plan builder, so the plans match the runtime's.
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

// Refusals, one static body each so each can be forked.

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
  // Projection widened but the guest clip not: the field would be cropped.
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

// Display-area cross-check on the shipping reader: only the leaf's stored word is perturbed, to BATTLE's 256 `screen`
// literal.
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

// The same reader handed a struct outside guest RAM.
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
  // Install the title runtime so each Core gets its per-Core context; no image is needed.
  vagrant::VagrantRuntime runtime;
  psxport_install_game(runtime);

  // 0. With no widening policy the framework resolves the guest projection at 4:3.
  expect(runtime.guestWidescreenProjection() == nullptr,
         "VagrantRuntime must publish no guest widescreen policy while the clip boundary stands");

  // 1. The measured publication.
  const vagrant::BattleProjectionPublication publication = measure();
  expect(publication.centreX == kRetailCentreX, "the measured horizontal centre must be the guest's own");
  expect(publication.centreY == 112, "the measured vertical centre must be the guest's own");
  expect(publication.screenDistance == kRetailScreenDistance, "the measured screen distance must be the guest's own");
  expect(publication.drawWidth == kRetailWidth, "the measured width must be the guest's own rectangle");
  expect(publication.drawHeight == kRetailHeight, "the measured height must be the guest's own rectangle");
  expect(publication.valid(), "a complete publication must report itself valid");

  // 2. The 4:3 identity, by construction.
  const auto identity = vagrant::BattleProjectionOwner::derive(publication, planFor(PresentationAspect::Standard4x3));
  expect(!identity.widens, "a 4:3 plan must not claim a widening");
  expect(identity.centreX == publication.centreX, "4:3 must pass the measured centre through untouched");
  expect(identity.drawWidth == publication.drawWidth, "4:3 must pass the measured width through untouched");

  // 3. Positive control: widening centre and clip in lockstep must widen.
  const auto wide = vagrant::BattleProjectionOwner::derive(publication, planFor(PresentationAspect::Wide16x9));
  expect(wide.widens, "a plan widening centre and clip together must produce a widening");
  expect(wide.centreX == 214, "the widened centre must be half the widened width, which is 214 at 16:9");
  expect(wide.drawWidth == 428, "the widened clip must be 428 px at 16:9 from a 320 px retail width");
  expect(wide.clipRight == wide.drawWidth - 1, "the clip's right edge must be the widened width's last column");

  // 4. The refusals.
  expect(diesOnSignal(refusesIncompletePublication), "an incomplete publication must be refused");
  expect(diesOnSignal(refusesUncentredRetail), "a retail centre that is not half the width must be refused");
  expect(diesOnSignal(refusesUnwidenedClip), "a plan that widens the projection but not the clip must be refused");
  expect(diesOnSignal(refusesInconsistentClipEdge), "a clip right edge past the widened width must be refused");
  expect(diesOnSignal(refusesOffCentreWidening), "a widened centre that is not half the widened width must be refused");
  expect(diesOnSignal(refusesUnusablePlan), "a plan with no guest draw width must be refused");
  expect(diesOnSignal(refusesDrawAreaDisagreement),
         "a publication whose own width word disagrees with the stated width must be refused");
  expect(diesOnSignal(refusesNonGuestRamArea), "a display area outside guest RAM must be refused rather than read");

  // 5. Registration refuses an address with no active image.
  {
    Fixture empty(false);
    expect(!vagrant::installBattleProjection(empty.core, empty.resident),
           "installing against a Core with no active image must be refused");
  }

  // 6. Registration refuses an unpublished identity; overlays share base 0x80068800.
  {
    Fixture fixture;
    expect(!vagrant::installBattleProjection(fixture.core, psx::cpu::ImageIdentity{.id = 9999u, .generation = 1u}),
           "installing against a foreign image identity must be refused");
    expect(vagrant::installBattleProjection(fixture.core, fixture.resident),
           "the same Core must still accept its own identity afterwards");
  }

  // 7. The guest-RAM bound.
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

  // 7b. With BATTLE's rectangle still zero BSS, the boot's 320-wide publication (`_initScreen` 0x80042054, call
  // 0x800420F0) must survive.
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

  // 7c. Guest states 320 while the leaf stored 256 (BATTLE's `screen` literal): the shipping reader must refuse.

  // 7d. The owner performs the GTE leaves; the fixture seeds nothing and reads both destinations back.
  {
    Fixture gte;
    expect(vagrant::installBattleProjection(gte.core, gte.resident),
           "the GTE fixture must install the same four leaves");
    // The centre leaf alone, apart from the screen distance leaf sharing `$a0`.
    runCentre(gte);
    expect(gte_read_ctrl(facts::kGteControlOfx) == (static_cast<std::uint32_t>(kRetailCentreX) << 16),
           "SetGeomOffset must have moved CR24 itself, not merely recorded an argument");
    expect(gte_read_ctrl(facts::kGteControlOfy) == (static_cast<std::uint32_t>(kPresenterCentreY) << 16),
           "SetGeomOffset must have moved CR25 itself");
    expect(gte.core.rsub.projParams.geomOfx() == static_cast<float>(kRetailCentreX) &&
               gte.core.rsub.projParams.geomOfy() == static_cast<float>(kPresenterCentreY),
           "the port's own projection record must move with the coprocessor, which is what makes the "
           "centre cross-check two statements rather than one");
    // The leaf's `sll` words at 0x80041540 leave `$a0` unshifted; the owner must too.
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

  // 8. The projection distance is never widened. Thresholds: 0x80074580 (`< 272`), 0x80074744 (`> 272`, spelled `<
  // 273`), and the zoom step at 0x80078578 that adds 64 and clamps at 0x300 = 768.
  expect(facts::kProjectionDistanceBranchThreshold == 272,
         "the gameplay threshold the projection-distance word is branched on must be recorded");
  expect(facts::kProjectionDistanceZoomClamp == 768,
         "the zoom clamp on the same word must be recorded; it is a second gameplay threshold");
  expect(facts::kProjectionDistanceZoomStep == 64, "the per-step growth of the projection distance must be recorded");
  expect(facts::kProjectionDistanceZoomStep != 0 &&
             facts::kProjectionDistanceZoomStep < facts::kProjectionDistanceBranchThreshold,
         "the game must drive the projection distance across the branch threshold, or the hazard is not a hazard");

  // 9. The two vertical centres, 128 and 112.
  expect(facts::kBattlePublicationCentreY == 128,
         "the overlay publication's own vertical centre at 320x240 must be recorded as 128");
  expect(facts::kBattlePresenterCentreY == 112,
         "the presenter's per-field literal vertical centre must be recorded as 112");
  expect(facts::kBattlePublicationCentreY != facts::kBattlePresenterCentreY,
         "the two publication sites must be recorded as disagreeing, or the owner's reason for "
         "sitting on the leaf is not a reason");
  expect(facts::kBattlePresenterCentreX == 160 && facts::kBattlePublicationCentreY / 2 == 64,
         "the presenter's centre must remain the half-width the publication itself states");

  // 10. The BATTLE.PRG call site is 0x8008A288; 0x8008B0A4 is `and $t2, $t1, $t5` in a CLUT loop.
  expect(facts::kBattlePublicationCallSite == 0x8008A288u,
         "the BATTLE.PRG call site of the publication must be 0x8008A288 as read from the bytes");
  expect(facts::kInitBtlPublicationCallSite == 0x800FA69Cu,
         "the INITBTL.PRG call site of the publication must be 0x800FA69C as read from the bytes");

  // 11. 256 is the DISPENV `screen` rect literal, not a clip; the 4:3 identity proves it scales nothing.
  expect(facts::kPublicationScreenWidth == 256 && facts::kPublicationScreenHeight == 224,
         "the publication's `screen` rect must be recorded as the 256x224 literals the bytes show");
  expect(facts::kPublicationScreenWidth != facts::kPublicationScreenHeight,
         "the `screen` rect is not square, so a reader cannot mistake one for the other");

  // 12. The blocker names the display resolution.
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
