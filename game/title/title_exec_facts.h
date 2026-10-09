#pragma once

#include <cstdint>

namespace vagrant::title_exec {

// TITLE `vs_title_exec` 0x80071334: 0x40-byte frame, callee-saved registers at sp+0x18.. and ra at sp+0x3C.
inline constexpr std::uint32_t kFrameSize = 0x40u;
inline constexpr std::uint32_t kSavedRa = 0x3Cu;
inline constexpr std::uint32_t kSavedFp = 0x38u;
inline constexpr std::uint32_t kSavedS0 = 0x18u;

// The `do {` top just after `menuItem = _saveFileExists()` (0x800713A8): s2 = menuItem, s7 = 1, fp = 0x800E0000.
inline constexpr std::uint32_t kLoopTop = 0x800713ACu;
inline constexpr std::uint32_t kDataBase = 0x800E0000u;

// vs_main_execTitle's instruction after the `jal` to TITLE (0x80042BD8 + 8).
inline constexpr std::uint32_t kReturn = 0x80042BE0u;

} // namespace vagrant::title_exec
