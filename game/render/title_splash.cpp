#include "render/title_splash.h"

#include "core.h"
#include "core/resident_facts.h"
#include "render/title_splash_facts.h"

#include <cstdlib>
#include <lucent/log.h>

namespace {

void writeRect(Core &core, std::uint32_t address, std::int16_t x, std::int16_t y, std::int16_t w, std::int16_t h) {
  core.mem_w16(address, static_cast<std::uint16_t>(x));
  core.mem_w16(address + 2u, static_cast<std::uint16_t>(y));
  core.mem_w16(address + 4u, static_cast<std::uint16_t>(w));
  core.mem_w16(address + 6u, static_cast<std::uint16_t>(h));
}

} // namespace

namespace vagrant {

TitleSplashPhase::TitleSplashPhase() : TitleSplashPhase(productionResidentCallServices()) {}

TitleSplashPhase::TitleSplashPhase(ResidentCallServices services) : services_(services) {
  if (!services_.call0 || !services_.call1 || !services_.call2 || !services_.call4) {
    lucent::error("vagrant-title", "TitleSplashPhase requires every finite guest-call service");
    std::abort();
  }
}

void TitleSplashPhase::begin(Core &core) {
  if (state_ != TitleSplashState::Cold) {
    lucent::error("vagrant-title", "TITLE splash began more than once");
    std::abort();
  }

  monoSound_ = core.mem_r8(title_splash::kSettings + 10u);
  vibrationOn_ = core.mem_r8(title_splash::kSettings + 11u);
  services_.call4(core, title_splash::kMemset, title_splash::kSettings, 0u, 0x20u, 0u);
  core.mem_w16(title_splash::kSettings + 2u, 0x02D8u);
  core.mem_w8(title_splash::kSettings + 8u, 1u);
  core.mem_w8(title_splash::kSettings + 9u, 3u);
  core.mem_w32(title_splash::kSettings, core.mem_r32(title_splash::kSettings) | 0x30u);
  core.mem_w8(title_splash::kSettings + 1u, 1u);

  // _displayPublisherAndDeveloper keeps this exact 0xB0-byte frame live across both 364-field loops.
  core.r[29] -= 0xB0u;
  const std::uint32_t rect = core.r[29] + 0x90u;
  writeRect(core, rect, 0, 0, 320, 512);
  services_.call4(core, title_splash::kClearImage, rect, 0u, 0u, 0u);
  services_.call4(core, title_splash::kDrawImage, 0x00400140u, title_splash::kPublisherData, 0x00010010u, 0u);
  services_.call4(core, title_splash::kDrawImage, 0x00000140u, title_splash::kPublisherData + 32u, 0x00300040u, 0u);

  const std::uint32_t disp = core.r[29] + 0x18u;
  const std::uint32_t draw = core.r[29] + 0x30u;
  core.mem_w32(core.r[29] + 0x10u, 240u);
  services_.call4(core, title_splash::kSetDefDispEnv, disp, 0u, 256u, 320u);
  core.mem_w32(core.r[29] + 0x10u, 240u);
  services_.call4(core, title_splash::kSetDefDrawEnv, draw, 0u, 0u, 320u);
  core.mem_w16(disp + 10u, 8u);
  core.mem_w16(disp + 14u, 224u);
  services_.call1(core, title_splash::kPutDispEnv, disp);
  services_.call1(core, title_splash::kPutDrawEnv, draw);
  services_.call1(core, title_splash::kDrawSync, 0u);
  state_ = TitleSplashState::InitialFieldWait;
}

void TitleSplashPhase::setDisplayEnvironments(Core &core, std::uint32_t index) {
  const std::uint32_t disp = core.r[29] + 0x18u;
  const std::uint32_t draw = core.r[29] + 0x30u;
  core.mem_w32(core.r[29] + 0x10u, 240u);
  services_.call4(core, title_splash::kSetDefDispEnv, disp, 0u, (index & 1u) * 256u, 320u);
  core.mem_w32(core.r[29] + 0x10u, 240u);
  services_.call4(core, title_splash::kSetDefDrawEnv, draw, 0u, (1u - (index & 1u)) * 256u, 320u);
  core.mem_w16(disp + 10u, 8u);
  core.mem_w16(disp + 14u, 224u);
}

void TitleSplashPhase::beginPublisherField(Core &core) {
  std::uint32_t fade = 0u;
  if (fieldIndex_ < 32u) {
    fade = (31u - fieldIndex_) * 4u;
  } else if (fieldIndex_ > 331u) {
    fade = (fieldIndex_ - 331u) * 4u;
  }
  services_.call4(core, title_splash::kDrawSprite, 0x00580020u, 0x10140000u, 0x00300100u, (fade << 16u) | 5u);
  setDisplayEnvironments(core, fieldIndex_);
  state_ = TitleSplashState::PublisherFieldWait;
}

void TitleSplashPhase::beginDeveloperField(Core &core) {
  std::uint32_t fade = 0u;
  if (fieldIndex_ < 32u) {
    fade = (31u - fieldIndex_) * 4u;
  } else if (fieldIndex_ > 331u) {
    fade = (fieldIndex_ - 331u) * 4u;
  } else if ((core.mem_r32(title_splash::kButtonsState) & 0xFFFFu) != 0u) {
    fieldIndex_ = 331u;
  }
  services_.call4(core, title_splash::kDrawSprite, 0x00680060u, 0x3F40F000u, 0x000D0080u, fade << 16u);
  setDisplayEnvironments(core, fieldIndex_);
  state_ = TitleSplashState::DeveloperFieldWait;
}

void TitleSplashPhase::finishEnvironment(Core &core) {
  services_.call1(core, title_splash::kSetDispMask, 0u);
  core.r[29] += 0xB0u;
  core.mem_w8(title_splash::kSettings + 10u, monoSound_ != 0u ? 1u : 0u);
  core.mem_w8(title_splash::kSettings + 11u, vibrationOn_ != 0u ? 1u : 0u);
  services_.call1(core, title_splash::kSetMonoSound, core.mem_r8(title_splash::kSettings + 10u));
  services_.call1(core, title_splash::kSetCdVolume, 0x7Fu);
  services_.call4(core, title_splash::kMemset, title_splash::kInventoryIndices, 0u, 0xB0u, 0u);
  core.mem_w8(title_splash::kStateFlags + 1u, 1u);
  core.mem_w8(title_splash::kStateFlags + 0x11Cu, 1u);
  state_ = TitleSplashState::Complete;
}

void TitleSplashPhase::advanceAfterField(Core &core) {
  if (state_ == TitleSplashState::Cold || state_ == TitleSplashState::Complete) {
    return;
  }
  if (state_ == TitleSplashState::InitialFieldWait) {
    services_.call1(core, title_splash::kSetDispMask, 1u);
    fieldIndex_ = 0u;
    beginPublisherField(core);
    return;
  }

  const std::uint32_t disp = core.r[29] + 0x18u;
  const std::uint32_t draw = core.r[29] + 0x30u;
  if (state_ == TitleSplashState::DeveloperFieldWait) {
    services_.call0(core, title_splash::kProcessPadState);
  }
  services_.call1(core, title_splash::kPutDispEnv, disp);
  services_.call1(core, title_splash::kPutDrawEnv, draw);
  if (++fieldIndex_ < 364u) {
    if (state_ == TitleSplashState::PublisherFieldWait) {
      beginPublisherField(core);
    } else {
      beginDeveloperField(core);
    }
    return;
  }
  if (state_ == TitleSplashState::PublisherFieldWait) {
    services_.call4(core, title_splash::kDrawImage, 0x00F00000u, title_splash::kDeveloperData, 0x000E0020u, 0u);
    fieldIndex_ = 0u;
    beginDeveloperField(core);
    return;
  }
  finishEnvironment(core);
}

} // namespace vagrant
