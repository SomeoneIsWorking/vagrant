#pragma once

#include <cstdint>

class Core;

namespace vagrant::heap {

// Guest call sites the allocator is native: `_sysReinit` at 0x80042B2C and `vs_main_initHeap` at 0x80043F74.
inline constexpr std::uint32_t kInitHeap = 0x80043F74u;
inline constexpr std::uint32_t kControlA = 0x800501A8u;
inline constexpr std::uint32_t kControlB = 0x800501B8u;

// Arena `_sysReinit` builds at 0x80042B2C, above the loaded image.
inline constexpr std::uint32_t kArenaBase = 0x8010C000u;
inline constexpr std::uint32_t kArenaSize = 0xF2000u;

static_assert(kControlB == kControlA + 16u, "the two free-list heads are adjacent 12-byte records rounded to 16");

// `vs_main_HeapHeader`: an allocated/free block, or an empty chain head.
struct HeapHeader {
  std::uint32_t prev;
  std::uint32_t next;
  std::uint32_t blockSz; // capacity in 16-byte units for a node, 0 for a chain head
};

// Seeds heapA with the arena as one free block and leaves heapB an empty chain.
void initHeap(Core *core);

} // namespace vagrant::heap
