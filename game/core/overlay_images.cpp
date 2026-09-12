#include "overlay_images.h"

#include "core.h"
#include "invalidation.h"
#include "lucent/content.h"

#include <algorithm>
#include <cstring>
#include <limits>
#include <utility>

namespace vagrant {
namespace {

// SHA-256 of the same owned files whose SHA-1 and load bases are independently checked by
// tools/extract_overlays.py and tools/re_overlay.py. The digest is checked again at publication,
// so an extracted file changed after provisioning cannot enter the executable cache.
const std::array<OverlaySpec, 3> kRetailOverlays{{
    {OverlayKind::Title,
     "TITLE.PRG",
     0x80068800u,
     554568u,
     "6370c7d1af22d448ce9c4d4863e5e78d71a77749bf160326dbec49b6cf188112"},
    {OverlayKind::Battle,
     "BATTLE.PRG",
     0x80068800u,
     577828u,
     "ad6914c81be92a008af8dece6ad394ce39c5aa42360542b5531716ebd00bba12"},
    {OverlayKind::InitBattle,
     "INITBTL.PRG",
     0x800F9800u,
     7036u,
     "c2d6eeb4347b01b3e2ffaf5a812a074601f1878ce8399f48e1e2adad943024fc"},
}};

std::optional<std::size_t> slotFor(std::uint32_t guestBase) {
  if (guestBase == 0x80068800u) {
    return 0;
  }
  if (guestBase == 0x800F9800u) {
    return 1;
  }
  return std::nullopt;
}

bool aliasesRam(const Core &core, std::span<const std::uint8_t> bytes) {
  const auto input = reinterpret_cast<std::uintptr_t>(bytes.data());
  const auto ram = reinterpret_cast<std::uintptr_t>(core.ram);
  return input > std::numeric_limits<std::uintptr_t>::max() - bytes.size() ||
         (input < ram + sizeof(core.ram) && input + bytes.size() > ram);
}

} // namespace

OverlayImages::OverlayImages(Core &core) : core_(core), specs_(kRetailOverlays) {}

OverlayImages::OverlayImages(Core &core, std::array<OverlaySpec, 3> specs) : core_(core), specs_(std::move(specs)) {}

OverlayLoadResult OverlayImages::load(OverlayKind kind, std::span<const std::uint8_t> bytes) {
  const auto found = std::find_if(specs_.begin(), specs_.end(), [kind](const OverlaySpec &spec) {
    return spec.kind == kind;
  });
  if (found == specs_.end()) {
    return {std::nullopt, "unknown Vagrant overlay kind"};
  }
  const auto slot = slotFor(found->guestBase);
  const auto physical = found->guestBase & 0x1fffffffu;
  if (!slot || found->name.empty() || found->byteCount == 0 || (found->guestBase & 3u) != 0 ||
      found->byteCount > sizeof(core_.ram) - physical || bytes.size() != found->byteCount) {
    return {std::nullopt, std::string(found->name) + " has an invalid measured load range or byte count"};
  }
  if (aliasesRam(core_, bytes)) {
    return {std::nullopt, std::string(found->name) + " input aliases destination RAM"};
  }
  const auto digest = lucent::content::sha256({reinterpret_cast<const std::byte *>(bytes.data()), bytes.size()});
  if (lucent::content::sha256_hex(digest) != found->sha256) {
    return {std::nullopt, std::string(found->name) + " SHA-256 differs from the authenticated retail image"};
  }
  if (core_.currentImageIdentity(found->guestBase) != active_[*slot]) {
    return {std::nullopt, std::string(found->name) + " slot residency changed outside its owner"};
  }

  std::uint64_t contentIdentity = 0;
  for (unsigned index = 0; index < sizeof(contentIdentity); ++index) {
    contentIdentity |= static_cast<std::uint64_t>(digest[index]) << (index * 8);
  }
  const GuestAddressRange range{physical, physical + static_cast<std::uint32_t>(bytes.size())};
  std::memcpy(core_.ram + physical, bytes.data(), bytes.size());
  psx::cpu::notifyExecutableWrite(core_, range, psx::cpu::ExecutableWriteSource::ModuleLoad);
  if (active_[*slot]) {
    core_.imageCatalog().deactivate(*active_[*slot]);
  }
  const auto identity = core_.imageCatalog().activate(found->name, range, contentIdentity);
  active_[*slot] = identity;
  return {identity, {}};
}

} // namespace vagrant
