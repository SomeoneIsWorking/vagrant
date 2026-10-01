#include "battle_projection.h"

#include "core.h"
#include "core/dynarec_dispatch.h"
#include "execution_exit.h"
#include "game.h"
#include "native_dispatch.h"
#include "proj_params.h"
#include "vagrant_context.h"

#include <cstdlib>
#include <lucent/log.h>

namespace {

namespace facts = vagrant::battle_projection;

// The guest's argument registers at each leaf, named so the numbers carry their meaning. These are
// the ABI, not title facts: `SetGeomOffset(long ofx, long ofy)` takes its two arguments in a0/a1,
// `SetDefDispEnv(DISPENV*, int x, int y, int w, int h)` its fourth in a3, and both env leaves take
// their fifth on the stack, which is why the height is read back from the struct the leaf filled
// rather than from a register the leaf has already consumed.
constexpr int kCentreXArgument = 4;
constexpr int kCentreYArgument = 5;
constexpr int kScreenDistanceArgument = 4;
constexpr int kEnvPointerArgument = 4;
constexpr int kDrawWidthArgument = 7;

[[noreturn]] void refuse(const char *what) {
  lucent::error("vagrant-proj", "SLUS_010.40 guest projection owner: {}", what);
  std::abort();
}

[[noreturn]] void refuseDisagreement(const char *what, int stated, int published) {
  lucent::error("vagrant-proj",
                "SLUS_010.40 guest projection owner: {} — the framework recorded {} and the "
                "coprocessor holds {}, so the leaf is not the one this owner was written against",
                what,
                stated,
                published);
  std::abort();
}

vagrant::BattleProjectionOwner *ownerFor(Core *core, const char *leaf) {
  if (!core || !core->gameCtx) {
    lucent::error("vagrant-proj", "SLUS_010.40 {} override ran without this title's context", leaf);
    std::abort();
  }
  return &static_cast<vagrant::VagrantContext *>(core->gameCtx)->battleProjection;
}

// The GTE control registers the two leaves write, and the framework's per-Core record of the values
// they were handed. Reading BOTH is what makes this a measurement rather than an echo: the leaf's
// entire behaviour is `CR24 = ofx << 16`, so a disagreement means either the address moved or the
// leaf is not a leaf, and both are named failures rather than a value this owner invented.
std::int32_t publishedCentreX(const Core &core) {
  return static_cast<std::int32_t>(gte_read_ctrl(facts::kGteControlOfx) >> 16);
}

std::int32_t publishedCentreY(const Core &core) {
  return static_cast<std::int32_t>(gte_read_ctrl(facts::kGteControlOfy) >> 16);
}

std::int32_t publishedScreenDistance(const Core &core) {
  return static_cast<std::int32_t>(gte_read_ctrl(facts::kGteControlH) & 0xFFFFu);
}

} // namespace

namespace vagrant {

void BattleProjectionOwner::publishCentre(Core &core) {
  // The title's OWN argument, at this instant. This is the base a widening would ride and the reason
  // the widening is idempotent by construction: the leaf is a pure function of its argument, the
  // coprocessor register is never fed back into it, and BATTLE's presenter passes a literal every
  // field, so yesterday's value is not retail — it is history.
  const auto statedX = static_cast<std::int32_t>(core.r[kCentreXArgument]);
  const auto statedY = static_cast<std::int32_t>(core.r[kCentreYArgument]);
  if (statedX < 0 || statedY < 0) {
    refuse("a guest centre was negative, so there is no centre to record");
  }

  // THE RETAIL BODY, performed rather than skipped. `SetGeomOffset` at 0x80041540 is five words:
  // two `sll` by 16 and two coprocessor register moves naming CR24 and CR25. The shift is
  // 16.16 fixed point, which psxport's `proj_params.h` already documents, and the primitive below is
  // the one implementation of the write AND of the port's own record of it — so this owner calls it
  // instead of restating the shift and keeping its own copy of the record to drift.
  libgte_set_geom_offset(&core, statedX, statedY);
  // The leaf leaves its arguments shifted into place, because its own body does. Reproducing that is
  // what makes this override byte-for-byte the leaf the framework's own HLE handler would have run;
  // a caller that read its own arguments back would see retail's values and not this port's.
  core.r[kCentreXArgument] = static_cast<std::uint32_t>(statedX) << 16;
  core.r[kCentreYArgument] = static_cast<std::uint32_t>(statedY) << 16;

  recordCentre(core, statedX, statedY);
}

void BattleProjectionOwner::publishScreenDistance(Core &core) {
  // RECORDED AND NEVER MODIFIED. `vs_main_projectionDistance` is not only a projection parameter:
  // two BATTLE functions branch on it against kProjectionDistanceBranchThreshold, and it scales the
  // GTE fog. A widening that raised it would flip a gameplay decision, so this leaf exists to make
  // "the owner never touches H" a checked fact rather than an intention, and to put the value the
  // run actually used on the record.
  const auto statedH = static_cast<std::int32_t>(core.r[kScreenDistanceArgument]);
  // `SetGeomScreen` at 0x80041534 is ONE coprocessor register move naming CR26 and `jr $ra`. It does
  // not transform its argument, so the primitive gets the value untouched.
  libgte_set_geom_screen(&core, statedH);
  recordScreenDistance(core, statedH);
}

void BattleProjectionOwner::recordCentre(Core &core, std::int32_t statedX, std::int32_t statedY) {
  const ProjParams &projection = core.rsub.projParams;
  const auto recordedX = static_cast<std::int32_t>(projection.geomOfx());
  const auto recordedY = static_cast<std::int32_t>(projection.geomOfy());
  if (recordedX != publishedCentreX(core)) {
    refuseDisagreement("horizontal centre", recordedX, publishedCentreX(core));
  }
  if (recordedY != publishedCentreY(core)) {
    refuseDisagreement("vertical centre", recordedY, publishedCentreY(core));
  }
  if (recordedX != statedX || recordedY != statedY) {
    lucent::error("vagrant-proj",
                  "SLUS_010.40 SetGeomOffset was handed OFX {} OFY {} and the framework recorded "
                  "{} and {}; a leaf that transforms its argument means this address is not the "
                  "leaf this owner was written against",
                  statedX,
                  statedY,
                  recordedX,
                  recordedY);
    std::abort();
  }

  retail_.centreX = recordedX;
  retail_.centreY = recordedY;
  centreSet_ = true;
}

void BattleProjectionOwner::recordScreenDistance(Core &core, std::int32_t statedH) {
  const ProjParams &projection = core.rsub.projParams;
  const auto recorded = static_cast<std::int32_t>(projection.geomH());
  const auto published = publishedScreenDistance(core);
  if (recorded != published) {
    refuseDisagreement("screen distance", recorded, published);
  }
  if (recorded != statedH) {
    lucent::error("vagrant-proj",
                  "SLUS_010.40 SetGeomScreen was handed {} and the coprocessor holds {}; refusing "
                  "to record a screen distance this owner cannot account for",
                  statedH,
                  published);
    std::abort();
  }
  if (recorded <= 0) {
    refuse("the guest stated a non-positive screen distance");
  }

  retail_.screenDistance = recorded;
  screenDistanceSet_ = true;
}

void BattleProjectionOwner::publishDisplayArea(Core &core, std::uint32_t leaf) {
  // THE TWO STATEMENTS OF ONE HORIZONTAL EXTENT, both captured BEFORE the retail body runs: the
  // register the guest stated, and — after the leaf has executed — the word the leaf stored it in.
  // Capturing the caller's `$a0` first matters, because that is the only statement of WHERE the
  // publication is: the address is the caller's, so it cannot be a constant this repository holds.
  const DisplayAreaPublication stated{.env = core.r[kEnvPointerArgument],
                                      .statedWidth = static_cast<std::int32_t>(core.r[kDrawWidthArgument])};

  // THE RETAIL BODY, RUN, through the framework's own owner of "call the original, it must return".
  // Both env leaves are finite and their whole effect is guest memory, so the guest's own body is
  // the correct implementation of them — the title's `screen` rect, the zeroed draw clip and the
  // display resolution are all written by the leaf, and an owner that skipped it would be the only
  // thing in the product that had ever written them.
  //
  // `psx::cpu::callOriginalToReturn` is the ONE implementation of that rule (native_dispatch.h) and
  // this file does not restate it. It also makes the right call here for a second reason: it ABORTS
  // on a budget exit, and for these two leaves that is the correct reading rather than a harsh one.
  // The measured bodies are 12 and about 20 instructions against a 564,480-cycle turn
  // (the measurement prints the page and the displacement separately, and
  // `kLeafEnvWidthOffset` below is gated on their sum), so a budget exit inside one of them means
  // the leaf at this address is not the leaf this owner was measured against — which is exactly the
  // failure this observation exists to catch. The other caller in this repository,
  // `vs_main_initHeap`, is the case that DOES need a resume, and it carries its own for the
  // framework's stated reason: see `docs/issues/0042`.
  psx::cpu::callOriginalToReturn(
      core, leaf, psx::cpu::ExecutionBudget::currentTurn(core), "Vagrant display-area publication");

  const PublishedArea area = readPublishedArea(core, stated);
  retail_.drawWidth = area.width;
  retail_.drawHeight = area.height;
  drawAreaSet_ = true;
}

PublishedArea BattleProjectionOwner::readPublishedArea(Core &core, const DisplayAreaPublication &stated) {
  // The width the title is publishing RIGHT NOW, cross-checked against the word the LEAF ITSELF
  // wrote: the argument, and the halfword at +4 of the struct the caller named. Two independent
  // statements of one horizontal extent, for ANY caller of either env leaf — which is the property
  // 0x8005DFD6 never had. The boot's `_initScreen` publishes 320 through this leaf and the overlay
  // publication publishes 320 through the same one, and each of them fills its own struct.
  if (stated.statedWidth <= 0) {
    refuse("the guest published a non-positive draw width");
  }
  const auto widthWord = stated.env + facts::kLeafEnvWidthOffset;
  const auto heightWord = stated.env + facts::kLeafEnvHeightOffset;
  if (!isGuestRam(widthWord) || !isGuestRam(heightWord)) {
    refuse("the display area the leaf was handed is not at a guest RAM address this owner may read");
  }

  const auto publishedWidth = core.mem_r16s(widthWord);
  const auto publishedHeight = core.mem_r16s(heightWord);
  if (publishedWidth != stated.statedWidth) {
    lucent::error("vagrant-proj",
                  "SLUS_010.40 published a {} wide draw area and the leaf stored {} at 0x{:08X}; "
                  "these are two statements of one horizontal extent and they disagree",
                  stated.statedWidth,
                  publishedWidth,
                  widthWord);
    std::abort();
  }
  if (publishedHeight <= 0) {
    refuse("the display area the leaf filled holds a non-positive height");
  }
  return {publishedWidth, publishedHeight};
}

WideBattleProjection BattleProjectionOwner::derive(const BattleProjectionPublication &retail,
                                                   const GuestProjectionPlan &plan) {
  if (!retail.valid()) {
    lucent::error("vagrant-proj",
                  "refusing to derive a projection from an incomplete publication (centre {}x{}, H "
                  "{}, area {}x{})",
                  retail.centreX,
                  retail.centreY,
                  retail.screenDistance,
                  retail.drawWidth,
                  retail.drawHeight);
    std::abort();
  }
  if (plan.nativeProjectionExtent.width <= 0 || plan.guestDrawWidth <= 0 || plan.projectionExtent.width <= 0) {
    lucent::error("vagrant-proj",
                  "the framework returned an unusable guest projection plan (native {} px, guest draw "
                  "{}, projection {})",
                  plan.nativeProjectionExtent.width,
                  plan.guestDrawWidth,
                  plan.projectionExtent.width);
    std::abort();
  }

  if (!plan.widescreen()) {
    // 4:3 IDENTITY, by construction: the plan's margin is zero at this aspect, so the title's own
    // measured values pass through untouched and nothing is restated.
    return {retail.centreX, retail.drawWidth, retail.drawWidth - 1, false};
  }

  // Refusal one. The publication states its own half-width centre, so a centre that is not that half
  // is a value this owner does not understand. Moving it to the plan's centre would then relocate
  // every primitive without widening the frustum — a translation published under a wide claim, which
  // is the exact failure the framework's presentation contract names.
  if (retail.centreX != retail.drawWidth / 2) {
    lucent::error("vagrant-proj",
                  "the measured centre {} is not the half of the measured width {}; deriving a "
                  "widening from it would translate the picture rather than widen it",
                  retail.centreX,
                  retail.drawWidth);
    std::abort();
  }

  // Refusal two, and it is the substantive one. A widening is the PAIR (centre, clip): widening the
  // centre alone slides the frustum right and crops its left edge off the field, showing no new
  // geometry at all. So the plan must widen the guest's clip to the same width as its projection, and
  // the clip's right edge must actually be the widened width. Until the overlay's display-area
  // publication is owned, this is where the derivation stops.
  if (plan.guestDrawWidth != plan.projectionExtent.width) {
    lucent::error("vagrant-proj",
                  "the plan widens the projection to {} px but the guest clip only to {} px; the "
                  "widened geometry would be clipped away, so refusing rather than publishing a "
                  "cropped frame as a widening",
                  plan.projectionExtent.width,
                  plan.guestDrawWidth);
    std::abort();
  }
  if (plan.guestClipRight != plan.guestDrawWidth - 1 || plan.projectionCenterX != plan.projectionExtent.width / 2) {
    lucent::error("vagrant-proj",
                  "the plan's clip right {} and centre {} do not describe a {} px wide frustum "
                  "centred on the {} px it claims",
                  plan.guestClipRight,
                  plan.projectionCenterX,
                  plan.guestDrawWidth,
                  plan.projectionExtent.width);
    std::abort();
  }

  return {plan.projectionCenterX, plan.guestDrawWidth, plan.guestClipRight, true};
}

bool BattleProjectionOwner::isGuestRam(std::uint32_t address) {
  // A NULL is never a valid record, and physical address 0 is the BIOS/KSEG-aliased region rather
  // than a title-owned word.
  constexpr std::uint32_t kKseg0Base = 0x80000000u;
  constexpr std::uint32_t kKseg1Base = 0xA0000000u;
  constexpr std::uint32_t kMainRamBytes = 0x00200000u;
  constexpr std::uint32_t kParallelRamBytes = 0x00100000u;

  if (address == 0) {
    return false;
  }
  if (address >= kKseg0Base && address - kKseg0Base < kMainRamBytes) {
    return true;
  }
  if (address >= kKseg1Base && address - kKseg1Base < kParallelRamBytes) {
    return true;
  }
  return address < kMainRamBytes;
}

BattleProjectionOwner &BattleProjectionOwner::from(Core &core) {
  auto *const owner = ownerFor(&core, "frame boundary");
  if (!owner->observed()) {
    lucent::error("vagrant-proj",
                  "the BATTLE projection owner was asked before the guest had stated a complete "
                  "viewport; there is nothing measured to act on yet");
    std::abort();
  }
  return *owner;
}

namespace {

void centreOverride(Core *core) {
  ownerFor(core, "SetGeomOffset")->publishCentre(*core);
}

void screenDistanceOverride(Core *core) {
  ownerFor(core, "SetGeomScreen")->publishScreenDistance(*core);
}

void drawAreaOverride(Core *core) {
  ownerFor(core, "SetDefDrawEnv")->publishDisplayArea(*core, facts::kSetDefDrawEnv);
}

void displayAreaOverride(Core *core) {
  ownerFor(core, "SetDefDispEnv")->publishDisplayArea(*core, facts::kSetDefDispEnv);
}

} // namespace

bool installBattleProjection(Core &core, psx::cpu::ImageIdentity residentImage) {
  const struct Binding {
    std::uint32_t address;
    const char *owner;
    psx::cpu::NativeFunction function;
  } bindings[]{
      {facts::kSetGeomOffset, "Vagrant SetGeomOffset", centreOverride},
      {facts::kSetGeomScreen, "Vagrant SetGeomScreen", screenDistanceOverride},
      {facts::kSetDefDrawEnv, "Vagrant SetDefDrawEnv", drawAreaOverride},
      {facts::kSetDefDispEnv, "Vagrant SetDefDispEnv", displayAreaOverride},
  };

  // Every leaf is resolved against the catalog BEFORE anything is installed, so a run is never left
  // half-registered: a rejected address means no override, not a subset of them. The resolution is
  // also what proves the address belongs to the image this Core published — the check that matters
  // here, because BATTLE, TITLE and ENDING all reuse load base 0x80068800 and an address alone
  // cannot say which module a leaf belongs to.
  for (const Binding &binding : bindings) {
    const auto resolved = core.currentImageIdentity(binding.address);
    if (!resolved) {
      lucent::error("vagrant-proj",
                    "{} at 0x{:08X} resolves to no active image, so it is not this title's resident "
                    "leaf; refusing to install any of the four",
                    binding.owner,
                    binding.address);
      return false;
    }
    if (*resolved != residentImage) {
      lucent::error("vagrant-proj",
                    "{} at 0x{:08X} resolves to a different active image generation than the "
                    "resident load published; refusing to install any of the four",
                    binding.owner,
                    binding.address);
      return false;
    }
  }

  // Installation goes through the title's one override seam so the run-end census counts these four
  // attempts alongside every other leaf, rather than a second table of "leaves this owner installed".
  for (const Binding &binding : bindings) {
    if (!dynarec::installNativeOverride(core, binding.address, binding.owner, binding.function, residentImage)) {
      return false;
    }
  }

  lucent::info("vagrant-proj",
               "guest projection publication owned: SetGeomOffset 0x{:08X}, SetGeomScreen "
               "0x{:08X}, SetDefDrawEnv 0x{:08X}, SetDefDispEnv 0x{:08X}. Observation only — no "
               "widening is applied, because {}",
               facts::kSetGeomOffset,
               facts::kSetGeomScreen,
               facts::kSetDefDrawEnv,
               facts::kSetDefDispEnv,
               facts::wideningBlocker());
  return true;
}

} // namespace vagrant
