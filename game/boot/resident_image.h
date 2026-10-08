#pragma once

#include "runtime/vagrant_runtime.h"

#include <cstddef>
#include <cstdint>
#include <filesystem>
#include <optional>
#include <string>
#include <string_view>
#include <vector>

class Core;

namespace vagrant {

// Catalog name of this generation and the disc environment key; provisioning names the same strings.
inline constexpr std::string_view kResidentImageName = "SLUS_010.40";
inline constexpr std::string_view kDiscEnvKey = "PSXPORT_VAGRANT_DISC";

// The whole provisioned file plus the digest of the bytes that will be mapped.
struct ResidentImage {
  std::vector<std::uint8_t> bytes;
  std::string sha256;
  std::size_t declaredSize = 0;
};

// Reads `path` whole and refuses unless it is exactly the measured SLUS_010.40 size.
// SHA-1 belongs to provisioning; header admission is `VagrantRuntime::loadResidentImage`.
std::optional<ResidentImage> readResidentImage(const std::filesystem::path &path);

// The measured file size: PS-X header plus text.
inline constexpr std::size_t kResidentFileBytes = 0x800u + kResidentHeader.textBytes;

} // namespace vagrant
