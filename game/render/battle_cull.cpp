#include "render/battle_cull.h"

#include "core.h"
#include "execution/dynarec_dispatch.h"
#include "game.h"

namespace vagrant::battle_cull {
namespace {

constexpr int kAt = 1;
constexpr int kFirstProjected = 8;
constexpr int kFirstResidue = 12;

std::int16_t lowHalf(std::uint32_t word) {
  return static_cast<std::int16_t>(word & 0xFFFFu);
}

std::int16_t highHalf(std::uint32_t word) {
  return static_cast<std::int16_t>(word >> 16);
}

bool anyBelow(const std::array<std::int32_t, 4> &values, int limit) {
  for (const std::int32_t value : values) {
    if (value < limit) {
      return true;
    }
  }
  return false;
}

bool anyAtLeast(const std::array<std::int32_t, 4> &values, int limit) {
  for (const std::int32_t value : values) {
    if (value >= limit) {
      return true;
    }
  }
  return false;
}

// The record canvas adds this many columns on each side of the displayed buffer.
int canvasMargin(const Core &core) {
  return core.game->guestDisplay.plan().presentationHorizontalMargin;
}

void rejectOverride(Core *core) {
  std::array<std::uint32_t, 4> projected{};
  for (std::size_t vertex = 0; vertex < projected.size(); ++vertex) {
    projected[vertex] = core->r[kFirstProjected + vertex];
  }
  const QuadVerdict verdict = testQuad(projected, widenedBox(canvasMargin(*core)));
  core->r[kAt] = verdict.visible ? 1u : 0u;
  for (std::size_t vertex = 0; vertex < verdict.residue.size(); ++vertex) {
    core->r[kFirstResidue + vertex] = static_cast<std::uint32_t>(verdict.residue[vertex]);
  }
}

} // namespace

ScreenBox widenedBox(int marginColumns) {
  ScreenBox box;
  box.left -= marginColumns;
  box.right += marginColumns;
  return box;
}

QuadVerdict testQuad(const std::array<std::uint32_t, 4> &projected, const ScreenBox &box) {
  std::array<std::int32_t, 4> rows{};
  std::array<std::int32_t, 4> columns{};
  for (std::size_t vertex = 0; vertex < projected.size(); ++vertex) {
    rows[vertex] = highHalf(projected[vertex]);
    columns[vertex] = lowHalf(projected[vertex]);
  }
  // Retail order: rows against the bottom, rows against the top, then columns against the left and the right.
  if (!anyBelow(rows, box.bottom) || !anyAtLeast(rows, box.top)) {
    return {false, rows};
  }
  if (!anyAtLeast(columns, box.left) || !anyBelow(columns, box.right)) {
    return {false, columns};
  }
  return {true, columns};
}

bool installBattleCull(Core &core) {
  return dynarec::installNativeOverride(core, kQuadReject, "Vagrant BATTLE room quad reject", rejectOverride);
}

} // namespace vagrant::battle_cull
