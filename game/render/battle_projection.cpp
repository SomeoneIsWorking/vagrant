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
// the ABI, not title facts: `SetGeomOffset(long ofx, long ofy)` takes its two arguments in a0/a1 and
// `SetDefDrawEnv(DRAWENV*, int x, int y, int w, int h)` its fourth in a3, with the fifth on the
// stack, which is why the height is taken from the guest's own rectangle instead of the frame.
constexpr int kCentreXArgument = 4;
constexpr int kCentreYArgument = 5;
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

void BattleProjectionOwner::observeCentre(Core &core) {
  // The title's OWN argument, at this instant. This is the base a widening would ride and the reason
  // the widening is idempotent by construction: the leaf is a pure function of its argument, the
  // coprocessor register is never fed back into it, and BATTLE's presenter passes a literal every
  // field, so yesterday's value is not retail — it is history.
  const auto statedX = static_cast<std::int32_t>(core.r[kCentreXArgument]);
  const auto statedY = static_cast<std::int32_t>(core.r[kCentreYArgument]);
  if (statedX < 0 || statedY < 0) {
    refuse("a guest centre was negative, so there is no centre to record");
  }

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

void BattleProjectionOwner::observeScreenDistance(Core &core) {
  // RECORDED AND NEVER MODIFIED. `vs_main_projectionDistance` is not only a projection parameter:
  // two BATTLE functions branch on it against kProjectionDistanceBranchThreshold, and it scales the
  // GTE fog. A widening that raised it would flip a gameplay decision, so this leaf exists to make
  // "the owner never touches H" a checked fact rather than an intention, and to put the value the
  // run actually used on the record.
  const auto stated = static_cast<std::int32_t>(core.r[kCentreXArgument]);
  const ProjParams &projection = core.rsub.projParams;
  const auto recorded = static_cast<std::int32_t>(projection.geomH());
  const auto published = publishedScreenDistance(core);
  if (recorded != published) {
    refuseDisagreement("screen distance", recorded, published);
  }
  if (recorded != stated) {
    lucent::error("vagrant-proj",
                  "SLUS_010.40 SetGeomScreen was handed {} and the coprocessor holds {}; refusing "
                  "to record a screen distance this owner cannot account for",
                  stated,
                  published);
    std::abort();
  }
  if (recorded <= 0) {
    refuse("the guest stated a non-positive screen distance");
  }

  retail_.screenDistance = recorded;
  screenDistanceSet_ = true;
}

void BattleProjectionOwner::observeDrawArea(Core &core) {
  // The width the title is publishing RIGHT NOW, cross-checked against the guest's own resident
  // rectangle. Two independent statements of one horizontal extent: the argument, and the word the
  // publication stores it in. If they disagree, this owner is not looking at the publication it was
  // written against, and a widening built on either number would be a guess wearing a measurement.
  const auto statedWidth = static_cast<std::int32_t>(core.r[kDrawWidthArgument]);
  if (statedWidth <= 0) {
    refuse("the guest published a non-positive draw width");
  }
  if (!isGuestRam(facts::kViewportWidthWord) || !isGuestRam(facts::kViewportHeightWord)) {
    refuse("the resident viewport rectangle is not at a guest RAM address this owner may read");
  }

  const auto rectangleWidth = core.mem_r16s(facts::kViewportWidthWord);
  const auto rectangleHeight = core.mem_r16s(facts::kViewportHeightWord);
  if (rectangleWidth != statedWidth) {
    lucent::error("vagrant-proj",
                  "SLUS_010.40 published a {} wide draw area while its own viewport rectangle holds "
                  "{}; these are two statements of one horizontal extent and they disagree",
                  statedWidth,
                  rectangleWidth);
    std::abort();
  }
  if (rectangleHeight <= 0) {
    refuse("the guest's own viewport rectangle holds a non-positive height");
  }

  retail_.drawWidth = rectangleWidth;
  retail_.drawHeight = rectangleHeight;
  drawAreaSet_ = true;
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
  ownerFor(core, "SetGeomOffset")->observeCentre(*core);
}

void screenDistanceOverride(Core *core) {
  ownerFor(core, "SetGeomScreen")->observeScreenDistance(*core);
}

void drawAreaOverride(Core *core) {
  ownerFor(core, "SetDefDrawEnv")->observeDrawArea(*core);
}

void displayAreaOverride(Core *core) {
  ownerFor(core, "SetDefDispEnv")->observeDrawArea(*core);
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
