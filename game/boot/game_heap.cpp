#include "boot/game_heap.h"

#include "core.h"

#include <cstddef>

namespace vagrant::heap {

// rood-reverse `vs_main_initHeap`.
void initHeap(Core *c) {
  const std::uint32_t node = c->r[4];  // a0: first arena block
  const std::uint32_t value = c->r[5]; // a1: arena size in bytes

  // The heapA head is a zero-capacity chain head; the arena node carries the capacity.
  c->mem_w32(kControlA + offsetof(HeapHeader, prev), node);
  c->mem_w32(kControlA + offsetof(HeapHeader, next), node);
  c->mem_w32(kControlA + offsetof(HeapHeader, blockSz), 0);

  // 16-byte units.
  HeapHeader arena{};
  arena.prev = kControlA;
  arena.next = kControlA;
  arena.blockSz = (value >> 4) - 1u;
  c->mem_w32(node + offsetof(HeapHeader, prev), arena.prev);
  c->mem_w32(node + offsetof(HeapHeader, next), arena.next);
  c->mem_w32(node + offsetof(HeapHeader, blockSz), arena.blockSz);

  // heapB starts as an empty self-linked chain.
  c->mem_w32(kControlB + offsetof(HeapHeader, prev), kControlB);
  c->mem_w32(kControlB + offsetof(HeapHeader, next), kControlB);
  c->mem_w32(kControlB + offsetof(HeapHeader, blockSz), 0);

  // Result registers callers read after setup.
  constexpr std::uint32_t kKseg0Base = 0x80050000u;
  c->r[2] = kControlB;
  c->r[3] = kKseg0Base;
}

} // namespace vagrant::heap
