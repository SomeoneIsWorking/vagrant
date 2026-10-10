// BATTLE's screen-space polygon reject, widened with the record canvas so the room draws into the margins.
#pragma once

#include <array>
#include <cstdint>

class Core;

namespace vagrant::battle_cull {

// The room's quad reject (func_80098014 in the decomp): a register-convention routine entered by `jal` with the four
// projected vertices in $t0-$t3 (x in the low half, y in the high half), answering in $at.
inline constexpr std::uint32_t kQuadReject = 0x80098014u;

// The retail screen the reject compares against: its immediates are 320 and 224.
inline constexpr int kRetailWidth = 320;
inline constexpr int kRetailHeight = 224;

// Half-open box in guest screen columns and rows.
struct ScreenBox {
  int left = 0;
  int right = kRetailWidth;
  int top = 0;
  int bottom = kRetailHeight;
};

// The retail box grown by `marginColumns` on each side; rows are never widened.
ScreenBox widenedBox(int marginColumns);

// What the routine leaves behind: $at, and the four sign-extended halves it last compared in $t4-$t7.
struct QuadVerdict {
  bool visible = false;
  std::array<std::int32_t, 4> residue{};
};

// Visible unless all four vertices lie past one side of the box. Identical to retail for the retail box.
QuadVerdict testQuad(const std::array<std::uint32_t, 4> &projected, const ScreenBox &box);

// Replaces the reject on the BATTLE generation that owns it; false when that image is not resident.
bool installBattleCull(Core &core);

} // namespace vagrant::battle_cull
