#include "core/game_heap.h"

#include "core.h"
#include "game.h"

#include <cstdio>
#include <memory>

// Hermetic contract of the first decomp-seeded native body (RE-07): vs_main_initHeap at
// 0x80043F74. tools/re_heap.py measures every constant below from SLUS_010.40 itself and
// --check-source fails when this file's shipped values drift from that measurement; this test
// pins the BEHAVIOUR the measured body must produce on a real Core.

namespace {

constexpr std::uint32_t kArenaBase = 0x8010C000u; // vs_main_initHeap's own caller argument
constexpr std::uint32_t kArenaSizeBytes = 0xF2000u;

int failures = 0;

void expect_word(const char *what, std::uint32_t got, std::uint32_t want) {
  if (got != want) {
    std::fprintf(stderr, "FAIL: %s: got 0x%08X want 0x%08X\n", what, got, want);
    ++failures;
  }
}

} // namespace

int main() {
  auto game = std::make_unique<Game>();
  Core *c = &game->core;

  // Guest ABI: a0 = first arena node, a1 = arena size (measured unique call site 0x80042B2C).
  c->r[4] = kArenaBase;
  c->r[5] = kArenaSizeBytes;
  c->r[2] = 0xDEADBEEFu;
  c->r[3] = 0xFEEDFACEu;

  vagrant::heap::initHeap(c);

  // heapA: both links point at the arena node, size field zeroed.
  expect_word("heapA.prev", c->mem_r32(vagrant::heap::kControlA + 0), kArenaBase);
  expect_word("heapA.next", c->mem_r32(vagrant::heap::kControlA + 4), kArenaBase);
  expect_word("heapA.blockSz", c->mem_r32(vagrant::heap::kControlA + 8), 0);

  // The arena node: linked back into heapA, holding size/16-1 blocks.
  expect_word("node.prev", c->mem_r32(kArenaBase + 0), vagrant::heap::kControlA);
  expect_word("node.next", c->mem_r32(kArenaBase + 4), vagrant::heap::kControlA);
  expect_word("node.blockSz", c->mem_r32(kArenaBase + 8), (kArenaSizeBytes >> 4) - 1);

  // heapB: self-linked empty chain.
  expect_word("heapB.prev", c->mem_r32(vagrant::heap::kControlB + 0), vagrant::heap::kControlB);
  expect_word("heapB.next", c->mem_r32(vagrant::heap::kControlB + 4), vagrant::heap::kControlB);
  expect_word("heapB.blockSz", c->mem_r32(vagrant::heap::kControlB + 8), 0);

  // Register leaves must match the substrate body exactly (mirror-verify compares v0/v1):
  // The measured retail body ends with v0 = &heapB and v1 = 0x80050000.
  expect_word("v0", c->r[2], vagrant::heap::kControlB);
  expect_word("v1", c->r[3], 0x80050000u);
  expect_word("a0 preserved", c->r[4], kArenaBase);

  if (failures) {
    std::fprintf(stderr, "game_heap contract: %d check(s) failed\n", failures);
    return 1;
  }
  std::printf("game_heap contract: 11/11 checks passed\n");
  return 0;
}
