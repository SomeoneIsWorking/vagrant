#pragma once

#include <cstdint>

namespace vagrant::title_memcard {

// SHA-bound TITLE.PRG facts measured by tools/re_title_memcard.py. The native owner keeps the
// overlay's allocation, pointer graph, image upload, reset policy, and event lifecycle, while the
// two retail CD-queue transfers are finite direct reads from the same disc extents.
inline constexpr std::uint32_t kOwner = 0x8006A49Cu;
inline constexpr std::uint32_t kAllocHeap = 0x80043EC4u;
inline constexpr std::uint32_t kDrawImage = 0x80068BDCu;
inline constexpr std::uint32_t kAllocateCdQueueSlot = 0x80044B10u;
inline constexpr std::uint32_t kFreeCdQueueSlot = 0x80044B80u;
inline constexpr std::uint32_t kCdEnqueue = 0x80044BC4u;
inline constexpr std::uint32_t kEnableReset = 0x80042C94u;
inline constexpr std::uint32_t kEnterCriticalSection = 0x80026974u;
inline constexpr std::uint32_t kOpenEvent = 0x800268D4u;
inline constexpr std::uint32_t kExitCriticalSection = 0x80026984u;
inline constexpr std::uint32_t kEnableEvent = 0x80026914u;

inline constexpr std::uint32_t kSpmcimgLba = 0x00014C98u;
inline constexpr std::uint32_t kSpmcimgSize = 0x0001C000u;
inline constexpr std::uint32_t kMcdataLba = 0x00014CD0u;
inline constexpr std::uint32_t kMcdataAndMcmanSize = 0x00002000u;

inline constexpr std::uint32_t kMcdataOffset = 0x00011400u;
inline constexpr std::uint32_t kTextTableOffset = 0x00001000u;
inline constexpr std::uint32_t kSaveFileInfoOffset = 0x00002000u;
inline constexpr std::uint32_t kDirectoryEntryOffset = 0x00002280u;

inline constexpr std::uint32_t kSpmcimgPointer = 0x800DEAB8u;
inline constexpr std::uint32_t kMcdataPointer = 0x800DEABCu;
inline constexpr std::uint32_t kTextTablePointer = 0x800DEAC0u;
inline constexpr std::uint32_t kDirectoryEntryPointer = 0x800DEB04u;
inline constexpr std::uint32_t kSaveFileInfoPointer = 0x800DEB08u;
inline constexpr std::uint32_t kEventDescriptors = 0x800DEA98u;
inline constexpr std::uint32_t kEventSpecs = 0x80072894u;
inline constexpr std::uint32_t kInitState = 0x800DC8C4u;

inline constexpr std::uint32_t kSpmcimgImageXy = 0x01000320u;
inline constexpr std::uint32_t kSpmcimgImageWh = 0x010000E0u;
inline constexpr std::uint32_t kSwCardEvent = 0xF4000001u;
inline constexpr std::uint32_t kHwCardEvent = 0xF0000011u;
inline constexpr std::uint32_t kEventModeNoInterrupt = 0x00002000u;
inline constexpr std::uint32_t kEventCount = 8u;

} // namespace vagrant::title_memcard
