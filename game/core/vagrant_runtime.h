#pragma once

#include "game_runtime.h"
#include "platform_hle.h"
#include "psx_exe_image.h"

#include <memory>
#include <span>
#include <string_view>

struct PlatformHlePlan;

namespace vagrant {

// Header facts are measured from the authenticated SLUS_010.40 image. They are kept separate from
// GuestProgramImage because the framework image view intentionally contains only runtime mapping
// facts; the title loader uses this complete header contract before publishing any bytes to Core.
struct ResidentHeaderFacts {
  std::uint32_t entry;
  std::uint32_t globalPointer;
  std::uint32_t textAddress;
  std::uint32_t textBytes;
  std::uint32_t stackBase;
  std::uint32_t stackOffset;
};

inline constexpr ResidentHeaderFacts kResidentHeader{
    .entry = 0x8001F544u,
    .globalPointer = 0u,
    .textAddress = 0x80010000u,
    .textBytes = 0x00052000u,
    .stackBase = 0x801FFFF0u,
    .stackOffset = 0u,
};

class VagrantRuntime final : public GameRuntime {
public:
  VagrantRuntime() = default;

  void *createContext(Core &) override;
  void destroyContext(void *context) override;
  void registerOverrides(Game &game) override;
  void bootInit(Core &core) override;
  const GuestProgramImage *guestProgramImage() const override;
  RenderCapabilities renderCapabilities() const override;
  bool guestVramIsPicture(const Game &game) const override;
  const char *discEnvVar() const override;
  // The measured libetc VSync body, and nothing else. psxport's product preflight REFUSES a title
  // with no measured VSync address before boot, because a guest busy-wait with no host frame
  // boundary reports a misleading timeout instead of the real defect.
  const PlatformHlePlan *platformHlePlan() const override;
  // The title-owned finite field. It is a non-null driver or the framework refuses the product loop
  // rather than dispatching a non-returning guest frame loop.
  std::unique_ptr<FrameDriver> createFrameDriver(Game &game) override;

  // DELIBERATELY NOT OVERRIDDEN, and the absence is the enforcement rather than an omission.
  // `guestWidescreenProjection()` is how a title advertises an aspect, and returning no policy makes
  // the framework resolve the guest projection at Standard4x3. Vagrant Story's owner
  // (`vagrant::BattleProjectionOwner`, game/render/battle_projection.h) measures the guest's
  // viewport publication and derives its widening, but applies none: the horizontal clip is published
  // by an overlay call whose VRAM layout this port has not read from bytes, so advertising a wide
  // aspect here would put a cropped frame on screen under a wide claim. Adding this override is the
  // last step of S010, not a wiring convenience — read
  // `vagrant::battle_projection::wideningBlocker()` first.

  // Authenticate the title-specific PS-X header, then delegate publication to psxport. The caller
  // authenticates the complete file identity before this boundary; this method additionally refuses
  // a different executable shape so a valid PS-X file from another title cannot be mapped as Vagrant.
  psx::cpu::PsxExeLoadResult
  loadResidentImage(Core &core, std::span<const std::uint8_t> bytes, std::string_view imageName) const;

private:
  static const GuestProgramImage programImage_;
  static const PlatformHlePlan platformPlan_;
};

} // namespace vagrant
