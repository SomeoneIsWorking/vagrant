#include "vagrant_runtime.h"

#include "core.h"
#include "core/native_owners.h"
#include "game.h"
#include "sync/frame_loop.h"
#include "sync/vsync_facts.h"
#include "vagrant_context.h"

#include <iomanip>
#include <sstream>

namespace vagrant {
namespace {

bool matchesResidentHeader(const psx::cpu::PsxExeImage &image) {
  return image.entry == kResidentHeader.entry && image.globalPointer == kResidentHeader.globalPointer &&
         image.textAddress == kResidentHeader.textAddress && image.textBytes == kResidentHeader.textBytes &&
         image.stackBase == kResidentHeader.stackBase && image.stackOffset == kResidentHeader.stackOffset;
}

std::string headerMismatch(const psx::cpu::PsxExeImage &image) {
  std::ostringstream detail;
  detail << "SLUS_010.40 PS-X EXE header mismatch: entry=0x" << std::hex << std::uppercase << image.entry << ", text=0x"
         << image.textAddress << "+0x" << image.textBytes;
  return detail.str();
}

} // namespace

// The measured libetc VSync body and its one-instruction admission window. `sync::kVSync` and
// `sync::kVSyncWindowEnd` come from the VBlank instrument's own derivation over the authenticated
// executable (RE-10); this is the mapping from that measurement to the framework's one typed field,
// and it is deliberately the only address admitted.
const PlatformHlePlan VagrantRuntime::platformPlan_ = [] {
  PlatformHlePlan plan{};
  plan.vsyncAddress = sync::kVSync;
  plan.windowLo[0] = sync::kVSync;
  plan.windowHi[0] = sync::kVSyncWindowEnd;
  return plan;
}();

const GuestProgramImage VagrantRuntime::programImage_{
    .bss = {0x80033678u, 0x800401A8u},
    .stackTopWordAddress = 0x80049138u,
    .stackReserveWordAddress = 0x8004913Cu,
    .heapBase = 0x800401A8u,
    .heapSizeStoreAddress = 0x80030FB8u,
    .heapBaseStoreAddress = 0x80030FB4u,
    .globalPointer = 0x80033674u,
    .libcInitEntry = 0x80026864u,
    .gameMainEntry = 0x80042C38u,
    .crt0Entry = 0x8001F544u,
    .residentText = {0x00010000u, 0x00062000u},
    .backtraceText = {},
    .stackBias = {true, -8},
};

void *VagrantRuntime::createContext(Core &core) {
  return new VagrantContext(core);
}

void VagrantRuntime::destroyContext(void *context) {
  delete static_cast<VagrantContext *>(context);
}

void VagrantRuntime::registerOverrides(Game &) {
  // Deliberately empty, and the emptiness is load-bearing. psxport calls this during product boot,
  // BEFORE any authenticated image exists, so `core.currentImageIdentity(address)` cannot resolve
  // anything here — and an address alone cannot identify PSX code in this title, because BATTLE,
  // TITLE and ENDING all load at 0x80068800. Image-scoped leaves are registered from the resident
  // publication boundary in `loadResidentImage` instead. See `game/core/native_owners.h`.
}

void VagrantRuntime::bootInit(Core &core) {
  // The measured resident bootstrap: the real finite leaf order, with every measured guest field wait
  // turned into an explicit host state the title's frame driver services. Owned by ResidentPhase;
  // this override is the single composition point that starts it.
  contextOf(core).residentPhase.begin(core);
}

const GuestProgramImage *VagrantRuntime::guestProgramImage() const {
  return &programImage_;
}

RenderCapabilities VagrantRuntime::renderCapabilities() const {
  return RenderCapabilities::direct();
}

bool VagrantRuntime::guestVramIsPicture(const Game &) const {
  return true;
}

const char *VagrantRuntime::discEnvVar() const {
  return "PSXPORT_VAGRANT_DISC";
}

const PlatformHlePlan *VagrantRuntime::platformHlePlan() const {
  return &platformPlan_;
}

std::unique_ptr<FrameDriver> VagrantRuntime::createFrameDriver(Game &) {
  return std::make_unique<VagrantFrameDriver>();
}

psx::cpu::PsxExeLoadResult
VagrantRuntime::loadResidentImage(Core &core, std::span<const std::uint8_t> bytes, std::string_view imageName) const {
  const auto parsed = psx::cpu::parsePsxExeImage(bytes);
  if (!parsed.image.has_value()) {
    return {std::nullopt, {}, parsed.detail};
  }
  if (!matchesResidentHeader(parsed.image.value())) {
    return {std::nullopt, {}, headerMismatch(parsed.image.value())};
  }
  const auto loaded = psx::cpu::loadPsxExeImage(core, bytes, imageName);
  if (!loaded) {
    return loaded;
  }
  // The resident generation is the only image that publishes the game's allocator initialiser and
  // the four viewport leaves, so their overrides become installable exactly here and at no other
  // boundary: `registerOverrides` runs at boot, before any image exists. A refusal is reported by
  // the owner and is not fatal here, because an unowned leaf is a missing measurement rather than a
  // wrong one.
  installResidentNativeOwners(core, loaded.identity.value());
  return loaded;
}

} // namespace vagrant
