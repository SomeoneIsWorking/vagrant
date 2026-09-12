#include "vagrant_runtime.h"

#include "core.h"
#include "game.h"

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

void *VagrantRuntime::createContext(Core &) {
  return nullptr;
}

void VagrantRuntime::destroyContext(void *) {
}

void VagrantRuntime::registerOverrides(Game &) {
}

void VagrantRuntime::bootInit(Core &) {
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

psx::cpu::PsxExeLoadResult
VagrantRuntime::loadResidentImage(Core &core, std::span<const std::uint8_t> bytes, std::string_view imageName) const {
  const auto parsed = psx::cpu::parsePsxExeImage(bytes);
  if (!parsed.image.has_value()) {
    return {std::nullopt, {}, parsed.detail};
  }
  if (!matchesResidentHeader(parsed.image.value())) {
    return {std::nullopt, {}, headerMismatch(parsed.image.value())};
  }
  return psx::cpu::loadPsxExeImage(core, bytes, imageName);
}

} // namespace vagrant
