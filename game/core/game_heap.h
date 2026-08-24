#pragma once

#include <cstdint>

class Core;

namespace vagrant::heap {

// RE-07, MEASURED by tools/re_heap.py from SLUS_010.40 itself: the image's only `jal` into its own
// allocator initialiser (0x80043F74, rood-reverse `vs_main_initHeap`) sits at 0x80042B2C inside
// `_sysReinit`, and the initialiser's own stores name the two free-list control blocks. The decomp's
// symbol_addrs names (heapA/heapB) corroborate; the bytes decide.
inline constexpr std::uint32_t kInitHeap = 0x80043F74u;
inline constexpr std::uint32_t kControlA = 0x800501A8u;
inline constexpr std::uint32_t kControlB = 0x800501B8u;

// The arena _sysReinit hands the initialiser at the unique call site 0x80042B2C
// (`lui a0,0x8010 / ori a0,a0,0xC000 / lui a1,0xF / jal / ori a1,a1,0x2000`) — above the loaded
// image, so it never overlaps code or data.
inline constexpr std::uint32_t kArenaBase = 0x8010C000u;
inline constexpr std::uint32_t kArenaSize = 0xF2000u;

static_assert(kControlB == kControlA + 16u, "the two free-list heads are adjacent 12-byte records rounded to 16");

// vs_main_HeapHeader (rood-reverse main.h): one allocated/free block or an empty chain head.
struct HeapHeader {
  std::uint32_t prev;
  std::uint32_t next;
  std::uint32_t blockSz; // capacity in 16-byte units for a node, 0 for a chain head
};

// initHeap — the guest ABI body replacing gen_func_80043F74: seeds heapA with [kArenaBase,
// kArenaBase+kArenaSize) as the single free block, leaves heapB an empty chain, and ends with
// v0 = &heapB and v1 = 0x80050000 exactly as the substrate body does (mirror-verify compares both).
void initHeap(Core *core);

// registerHeapOverride — wires (kInitHeap, initHeap, gen_func_80043F74) into the override registry
// via shard_set_override. A no-op unless the recompiled substrate is linked.
void registerHeapOverride();

} // namespace vagrant::heap
