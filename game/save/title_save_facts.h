#pragma once

#include <cstdint>

namespace vagrant::title_save {

// `_saveFileExists` facts; the 0x68-byte frame stays live.
inline constexpr std::uint32_t kOwner = 0x8006E988u;
inline constexpr std::uint32_t kGameTimeUpdate = 0x8004261Cu;
inline constexpr std::uint32_t kAsmNop = 0x8004908Cu;
inline constexpr std::uint32_t kProcessCdQueue = 0x80044C74u;
inline constexpr std::uint32_t kMemcardEventHandler = 0x8006947Cu;
inline constexpr std::uint32_t kRMemcpy = 0x80068C3Cu;
inline constexpr std::uint32_t kFirstFile = 0x80026B94u;
inline constexpr std::uint32_t kShutdownMemcard = 0x8006A6E0u;
inline constexpr std::uint32_t kFilenameTemplatePointer = 0x8007288Cu;

inline constexpr std::uint32_t kStackFrameSize = 0x68u;
inline constexpr std::uint32_t kFilenameOffset = 0x10u;
inline constexpr std::uint32_t kDirectoryEntryOffset = 0x38u;
inline constexpr std::uint32_t kFilenameSize = 22u;

} // namespace vagrant::title_save
