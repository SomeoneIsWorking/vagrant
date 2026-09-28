#pragma once

#include "vagrant_runtime.h"

#include <cstddef>
#include <cstdint>
#include <filesystem>
#include <optional>
#include <string>
#include <string_view>
#include <vector>

class Core;

namespace vagrant {

// The image name the framework's image catalog publishes this generation under. It is the retail
// disc name, so a run's log names the same file `tools/extract_exe.py` authenticated.
inline constexpr std::string_view kResidentImageName = "SLUS_010.40";

// The whole provisioned file, plus the digest of exactly the bytes that will be mapped. A run that
// prints this can name which file it executed, which is the first thing a later "that run proved
// nothing" review asks for.
struct ResidentImage {
  std::vector<std::uint8_t> bytes;
  std::string sha256;
  std::size_t declaredSize = 0;
};

// Read `path` WHOLE and refuse unless the file is exactly the measured SLUS_010.40 size. Nothing
// is parsed and no guest state is touched on the failing path, so a refusal is a refusal rather than
// a partially mapped image.
//
// WHAT THIS GATE IS NOT. It is not a second file-identity check. The file's SHA-1 against the
// vendored CC0 decompilation's own target belongs to provisioning, where `tools/extract_exe.py`
// already authenticates the extracted bytes before writing them to gitignored scratch.
// Re-deriving a hash here would be a second implementation of one rule with no new evidence.
// The structural admission that DOES belong here — the measured PS-X EXE signature, entry, text
// range and stack — is owned by `VagrantRuntime::loadResidentImage`, because only it knows the Core.
std::optional<ResidentImage> readResidentImage(const std::filesystem::path &path);

// The measured file size, derived from the header facts the image itself declares.
inline constexpr std::size_t kResidentFileBytes = 0x800u + kResidentHeader.textBytes;

} // namespace vagrant
