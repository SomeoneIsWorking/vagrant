#include "vagrant_runtime.h"

#include "cd/cd_facts.h"
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
// executable (RE-10); this is the mapping from that measurement to the framework's one typed field.
//
// An AGGREGATE initialiser, not a lambda: a lambda-initialised object with static storage duration
// can throw during construction and the exception cannot be caught, and nothing here can — every
// field is a `constexpr` address from a SHA-bound measurement, so there is nothing to compute and
// nothing that could fail.
const PlatformHlePlan VagrantRuntime::platformPlan_{
    // THE TWO STOCK libcd LEAVES, decided by the first authenticated run of this title rather than by
    // preference. With them undeclared they ran as guest code, and the boot's first host field
    // reached `CD_sync`'s completion wait, spun there, and exhausted the one-field cycle budget at
    // 0x8002105C after 564,502 guest cycles — a WAIT for a controller IRQ psxport's synchronous CD
    // model does not deliver, not compute. Resuming the turn would only spin again, so the leaves
    // are the framework's typed synchronous owners instead. `game/cd/cd_facts.h` already holds the
    // measured addresses and `tools/re_cd.py` already gates them; this is the declaration, not a
    // second measurement.
    .cdCommandAddress = cd::kCdCommand,
    .cdSyncAddress = cd::kCdSync,
    .vsyncAddress = sync::kVSync,
    // The libetc field counter retail `VSync` polls, and the only reason a NEGATIVE query is
    // permitted at all. Measured by the same SHA-bound instrument as `kVSync`, and cross-checked
    // there against VSync's own query, wait and completion paths, `startIntrVSync`, and the resident
    // VBlank handler. Omitting it is not "no negative queries": the guest's first VSync is one
    // (`CD_cw` calls `VSync(-1)`), and psxport refuses it by name rather than inventing a count.
    .vsyncQueryCounterAddress = sync::kVSyncQueryCounter,
    // One instruction per leaf, three exact windows of the four the framework holds. `CD_cw` and
    // `CD_sync` each contain waits whose guest bodies must stay UNREACHABLE, so admitting a range
    // here would admit the VSync loop this port exists to keep out of the guest.
    //
    // `stockCdWorkArea` is deliberately left zero. psxport's stock-CD path preserves the replaced
    // command routine's own guest bookkeeping through it, and this title has NOT measured the libcd
    // `CdLastPos` / last-mode bytes. Zero means that state stays guest-owned, which is the documented
    // default for an unmeasured address and is what the reference direct runtime (Spyro 1) also
    // declares. Publishing a guessed pair would be forging guest state, not owning it.
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
  // Not `const`: this is returned by value on the success path below, and a const local would make
  // that a copy rather than a move.
  auto loaded = psx::cpu::loadPsxExeImage(core, bytes, imageName);
  if (!loaded) {
    return loaded;
  }
  // Named here, and refused when absent, because every leaf below is registered AGAINST this
  // generation: an identity of zero would make the registration a lookup against nothing.
  const psx::cpu::ImageIdentity residentImage = loaded.identity.value_or(psx::cpu::ImageIdentity{});
  if (residentImage == psx::cpu::ImageIdentity{}) {
    return {std::nullopt, loaded.image, "the resident image published no generation identity"};
  }
  // The resident generation is the only image that publishes the game's allocator initialiser and
  // the four viewport leaves, so their overrides become installable exactly here and at no other
  // boundary: `registerOverrides` runs at boot, before any image exists. THIS IS THE ONLY CALL
  // SITE in the product — a second registration of the same table is a DUPLICATE key by
  // construction, and psxport's dispatcher refuses duplicates, so a second entry point turns a
  // working boot into a refused one.
  //
  // The all-or-nothing refusal lives HERE, at the boundary that owns the registration, rather than in
  // a caller that would have to re-run the registration to learn about it. A partially owned image is
  // a wrong measurement rather than a missing one, so the load itself is refused and the caller's
  // existing `!published` path reports it with this detail.
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
