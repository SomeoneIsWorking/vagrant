#include "boot/resident_image.h"

#include "lucent/content.h"
#include "lucent/log.h"

#include <fstream>
#include <iterator>

namespace vagrant {

std::optional<ResidentImage> readResidentImage(const std::filesystem::path &path) {
  std::ifstream file(path, std::ios::binary | std::ios::ate);
  if (!file) {
    return std::nullopt;
  }
  const auto measured = file.tellg();
  if (measured < 0) {
    return std::nullopt;
  }
  const auto size = static_cast<std::size_t>(measured);
  if (size != kResidentFileBytes) {
    lucent::error("vagrant-boot",
                  "{} is {} bytes; the measured SLUS_010.40 resident is {} bytes (0x800 PS-X header + "
                  "0x{:X} text). Refusing to map a different-sized file as this title's resident",
                  path.string(),
                  size,
                  kResidentFileBytes,
                  kResidentHeader.textBytes);
    return std::nullopt;
  }
  file.seekg(0);
  ResidentImage image{.bytes = std::vector<std::uint8_t>(size), .declaredSize = size};
  file.read(reinterpret_cast<char *>(image.bytes.data()), static_cast<std::streamsize>(size));
  if (file.gcount() != static_cast<std::streamsize>(size) || file.peek() != std::ifstream::traits_type::eof()) {
    lucent::error("vagrant-boot", "{} changed size or could not be read completely", path.string());
    return std::nullopt;
  }
  image.sha256 = lucent::content::sha256_hex(
      lucent::content::sha256({reinterpret_cast<const std::byte *>(image.bytes.data()), image.bytes.size()}));
  return image;
}

} // namespace vagrant
