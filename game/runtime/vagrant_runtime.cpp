#include "runtime/vagrant_runtime.h"

#include "boot/resident_facts.h"
#include "boot/resident_image.h"
#include "cd/cd_facts.h"
#include "core.h"
#include "execution/native_owners.h"
#include "game.h"
#include "runtime/vagrant_context.h"
#include "sync/frame_loop.h"
#include "sync/vsync_facts.h"

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

// libetc VSync body and its one-instruction admission window.
const PlatformHlePlan VagrantRuntime::platformPlan_{
    // The two stock libcd leaves are typed synchronous owners: as guest code the boot spun in CD_sync's completion wait
    // at 0x8002105C on a controller IRQ the synchronous CD model never delivers.
    .cdCommandAddress = cd::kCdCommand,
    .cdSyncAddress = cd::kCdSync,
    // Guest libapi DMA callback table: channel 4's slot body at 0x8001DE94 is the only clearer of the transfer flag
    // at 0x800377F0, which `_waitTransferAvailable` polls and `_initSound` parks in.
    .dmaCallbackTable = resident::kDmaCallbackTable,
    .vsyncAddress = sync::kVSync,
    // libetc field counter retail `VSync` polls; the guest's first VSync is `VSync(-1)` from `CD_cw`.
    .vsyncQueryCounterAddress = sync::kVSyncQueryCounter,
    // One instruction per leaf, so the `CD_cw` and `CD_sync` waits stay unreachable. `stockCdWorkArea` stays zero: the
    // libcd CdLastPos/last-mode bytes are unmeasured, so that state stays guest-owned.
    .windowLo = {sync::kVSync, cd::kCdCommand, cd::kCdSync},
    .windowHi = {sync::kVSyncWindowEnd, cd::kCdCommandWindowEnd, cd::kCdSyncWindowEnd},
};

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
  // Empty on purpose: this runs before any image exists, and overlays share 0x80068800.
  // Image-scoped leaves are registered from `loadResidentImage`.
}

void VagrantRuntime::bootInit(Core &core) {
  // Starts the resident bootstrap owned by ResidentPhase.
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
  return kDiscEnvKey.data();
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
  auto loaded = psx::cpu::loadPsxExeImage(core, bytes, imageName);
  if (!loaded) {
    return loaded;
  }
  // Every leaf is registered against this generation, so a zero identity is refused.
  const psx::cpu::ImageIdentity residentImage = loaded.identity.value_or(psx::cpu::ImageIdentity{});
  if (residentImage == psx::cpu::ImageIdentity{}) {
    return {std::nullopt, loaded.image, "the resident image published no generation identity"};
  }
  // The only registration site: `registerOverrides` runs before any image exists, and a second registration is a
  // duplicate key. Refusal is all-or-nothing, so a partially owned image fails the load.
  const auto registration = installResidentNativeOwners(core, residentImage);
  if (!registration) {
    return {std::nullopt,
            loaded.image,
            std::string{"the resident generation published but its native leaves were not fully "
                        "registered: installed "} +
                std::to_string(registration.installed) + " of " + std::to_string(registration.attempts) + ", " +
                std::to_string(registration.refused) + " refused, first at '" + registration.refusedOwner + "'"};
  }
  return loaded;
}

} // namespace vagrant
