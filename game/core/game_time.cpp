#include "core/game_time.h"

#include "core.h"
#include "core/resident_facts.h"

#include <cstdint>

namespace vagrant::game_time {

void advance(Core &core) {
  const std::uint8_t hours = core.mem_r8(resident::kGameTime + 3u);
  if (static_cast<std::int8_t>(hours) >= 100) {
    return;
  }
  const std::uint8_t frames =
      static_cast<std::uint8_t>(core.mem_r8(resident::kGameTime) + core.mem_r8(resident::kGameTimeTickSpeed));
  core.mem_w8(resident::kGameTime, frames);
  if (static_cast<std::int8_t>(frames) < 60) {
    return;
  }
  core.mem_w8(resident::kGameTime, 0u);
  const std::uint8_t seconds = static_cast<std::uint8_t>(core.mem_r8(resident::kGameTime + 1u) + 1u);
  core.mem_w8(resident::kGameTime + 1u, seconds);
  if (static_cast<std::int8_t>(seconds) < 60) {
    return;
  }
  core.mem_w8(resident::kGameTime + 1u, 0u);
  const std::uint8_t minutes = static_cast<std::uint8_t>(core.mem_r8(resident::kGameTime + 2u) + 1u);
  core.mem_w8(resident::kGameTime + 2u, minutes);
  if (static_cast<std::int8_t>(minutes) < 60) {
    return;
  }
  core.mem_w8(resident::kGameTime + 2u, 0u);
  const std::uint8_t nextHours = static_cast<std::uint8_t>(hours + 1u);
  core.mem_w8(resident::kGameTime + 3u, static_cast<std::int8_t>(nextHours) < 100 ? nextHours : 100u);
}

} // namespace vagrant::game_time
