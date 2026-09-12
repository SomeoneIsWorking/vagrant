#pragma once

#include "game_runtime.h"
#include "psx_exe_image.h"

#include <span>
#include <string_view>

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

  // Authenticate the title-specific PS-X header, then delegate publication to psxport. The caller
  // authenticates the complete file identity before this boundary; this method additionally refuses
  // a different executable shape so a valid PS-X file from another title cannot be mapped as Vagrant.
  psx::cpu::PsxExeLoadResult
  loadResidentImage(Core &core, std::span<const std::uint8_t> bytes, std::string_view imageName) const;

private:
  static const GuestProgramImage programImage_;
};

} // namespace vagrant
