#include "core/game_heap.h"

#include "core.h"
#include "override_registry.h"

#include <lucent/log.h>

#ifdef VAGRANT_HAVE_SUBSTRATE
extern void gen_func_80043F74(Core *);
extern void shard_set_override(std::uint32_t, void (*)(Core *));
#endif

// RE-07: the first native body seeded from the matching decomp. rood-reverse (CC0) main.c
// vs_main_initHeap is the readable source; every constant it names was re-measured from our own
// executable by tools/re_heap.py before shipping, and the live gate proves the override both
// installed and byte-matched the substrate body on the real boot path.
void vagrant::heap::initHeap(Core *c) {
  const std::uint32_t node = c->r[4];  // a0: first arena block
  const std::uint32_t value = c->r[5]; // a1: arena size in bytes

  // heapA becomes a one-block chain over the arena; its head records no capacity of its own.
  c->mem_w32(kControlA + offsetof(HeapHeader, prev), node);
  c->mem_w32(kControlA + offsetof(HeapHeader, next), node);
  c->mem_w32(kControlA + offsetof(HeapHeader, blockSz), 0);

  // The arena block links back into heapA and holds the capacity in 16-byte units.
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

  // Register leaves the substrate body also leaves; callers read v0 after an allocation query and
  // mirror-verify compares them per invocation.
  constexpr std::uint32_t kKseg0Base = 0x80050000u;
  c->r[2] = kControlB;
  c->r[3] = kKseg0Base;
}

void vagrant::heap::registerHeapOverride() {
#ifdef VAGRANT_HAVE_SUBSTRATE
  overrides::install(kInitHeap, "vs_main::initHeap", initHeap, gen_func_80043F74, shard_set_override);
#else
  lucent::debug("vagrant-heap", "heap registration deferred: no generated substrate in this target");
#endif
}
