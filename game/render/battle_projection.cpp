#include "render/battle_projection.h"

#include "core.h"
#include "execution/dynarec_dispatch.h"
#include "execution_exit.h"
#include "game.h"
#include "native_dispatch.h"
#include "proj_params.h"
#include "runtime/vagrant_context.h"

#include <cstdlib>
#include <lucent/log.h>

namespace {

namespace facts = vagrant::battle_projection;

// Guest argument registers at each leaf (ABI): SetGeomOffset takes a0/a1, SetDefDispEnv its width in a3, and both
// env leaves take the height on the stack.
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
  if (!core) {
    lucent::error("vagrant-proj", "SLUS_010.40 {} override ran with no Core", leaf);
    std::abort();
  }
  return &vagrant::contextOf(*core).battleProjection;
}

// The GTE control registers the leaves write; the leaf's whole effect is `CR24 = ofx << 16`.
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
  // The title's own argument; the register is never fed back, so a widening stays idempotent.
  const auto statedX = static_cast<std::int32_t>(core.r[kCentreXArgument]);
  const auto statedY = static_cast<std::int32_t>(core.r[kCentreYArgument]);
  if (statedX < 0 || statedY < 0) {
    refuse("a guest centre was negative, so there is no centre to record");
  }

  // SetGeomOffset (0x80041540) is two `sll` by 16 and two CR24/CR25 moves; the primitive owns the
  // write and psxport's record of it.
  libgte_set_geom_offset(&core, statedX, statedY);
  // The leaf leaves its arguments shifted, as its own body does.
  core.r[kCentreXArgument] = static_cast<std::uint32_t>(statedX) << 16;
  core.r[kCentreYArgument] = static_cast<std::uint32_t>(statedY) << 16;

  recordCentre(core, statedX, statedY);
}

void BattleProjectionOwner::publishScreenDistance(Core &core) {
  // Recorded, never modified: BATTLE branches on this word (kProjectionDistanceBranchThreshold).
  const auto statedH = static_cast<std::int32_t>(core.r[kScreenDistanceArgument]);
  // SetGeomScreen (0x80041534) is one CR26 move and does not transform its argument.
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
  // Capture the caller's `$a0` before the body runs; the struct address is the caller's.
  const DisplayAreaPublication stated{.env = core.r[kEnvPointerArgument],
                                      .statedWidth = static_cast<std::int32_t>(core.r[kDrawWidthArgument])};

  // Both env leaves only write guest memory, so the original body runs; a budget exit inside one means the leaf at
  // this address is not the one this owner was written against.
  dynarec::callOriginalToReturn(core, leaf, "Vagrant display-area publication");

  const PublishedArea area = readPublishedArea(core, stated);
  retail_.drawWidth = area.width;
  retail_.drawHeight = area.height;
  drawAreaSet_ = true;
}

PublishedArea BattleProjectionOwner::readPublishedArea(Core &core, const DisplayAreaPublication &stated) {
  // Cross-check the stated width against the halfword at +4 of the struct the caller named.
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
    // 4:3 identity: the plan's margin is zero.
    return {retail.centreX, retail.drawWidth, retail.drawWidth - 1, false};
  }

  // A centre that is not half the width would make this a translation, not a widening.
  if (retail.centreX != retail.drawWidth / 2) {
    lucent::error("vagrant-proj",
                  "the measured centre {} is not the half of the measured width {}; deriving a "
                  "widening from it would translate the picture rather than widen it",
                  retail.centreX,
                  retail.drawWidth);
    std::abort();
  }

  // A widening is the pair (centre, clip); widening only the centre crops the left edge.
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
  // Physical address 0 is the BIOS/KSEG-aliased region, not a title-owned word.
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

  // Resolve every leaf before installing any, so a rejected address leaves nothing half-installed.
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

  // Install through the title's one override seam.
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
