// The BATTLE room quad reject: retail at 4:3, widened by the canvas margin at 16:9.

#include "render/battle_cull.h"

#include <cstdint>
#include <cstdio>

namespace {

namespace cull = vagrant::battle_cull;

int failures = 0;

void expect(bool condition, const char *what) {
  if (!condition) {
    std::fprintf(stderr, "[FAIL] %s\n", what);
    ++failures;
  }
}

std::uint32_t vertex(int x, int y) {
  return static_cast<std::uint16_t>(x) | (static_cast<std::uint32_t>(static_cast<std::uint16_t>(y)) << 16);
}

std::array<std::uint32_t, 4> quad(int left, int right, int top, int bottom) {
  return {vertex(left, top), vertex(right, top), vertex(left, bottom), vertex(right, bottom)};
}

constexpr int kMargin = 54;

void retailBoxIsTheGuestScreen() {
  const cull::ScreenBox box = cull::widenedBox(0);
  expect(box.left == 0 && box.right == 320 && box.top == 0 && box.bottom == 224, "margin 0 is the 320x224 screen");
  expect(cull::testQuad(quad(10, 50, 10, 50), box).visible, "a quad inside is visible");
  expect(!cull::testQuad(quad(-60, -1, 10, 50), box).visible, "a quad left of the screen is rejected at retail");
  expect(!cull::testQuad(quad(320, 380, 10, 50), box).visible, "a quad right of the screen is rejected at retail");
}

void marginAdmitsTheWideColumns() {
  const cull::ScreenBox box = cull::widenedBox(kMargin);
  expect(box.left == -kMargin && box.right == 320 + kMargin, "the box grows by the margin on each side");
  expect(box.top == 0 && box.bottom == 224, "rows are never widened");
  expect(cull::testQuad(quad(-50, -5, 10, 50), box).visible, "a quad in the left margin is drawn");
  expect(cull::testQuad(quad(325, 370, 10, 50), box).visible, "a quad in the right margin is drawn");
  expect(!cull::testQuad(quad(-120, -kMargin - 1, 10, 50), box).visible, "a quad past the left margin is rejected");
  expect(!cull::testQuad(quad(320 + kMargin, 450, 10, 50), box).visible, "a quad past the right margin is rejected");
}

void rowsStayRetail() {
  const cull::ScreenBox box = cull::widenedBox(kMargin);
  expect(!cull::testQuad(quad(10, 50, -40, -1), box).visible, "a quad above the screen is rejected");
  expect(!cull::testQuad(quad(10, 50, 224, 260), box).visible, "a quad below the screen is rejected");
}

void aQuadSpanningTheEdgeIsVisibleAtRetail() {
  expect(cull::testQuad(quad(-30, 24, 10, 50), cull::widenedBox(0)).visible, "a straddling quad is visible");
}

void residueHoldsTheLastComparedValues() {
  const cull::QuadVerdict rows = cull::testQuad(quad(10, 50, -40, -1), cull::widenedBox(0));
  expect(rows.residue[0] == -40 && rows.residue[2] == -1, "a row reject leaves the row values");
  const cull::QuadVerdict columns = cull::testQuad(quad(-60, -1, 10, 50), cull::widenedBox(0));
  expect(columns.residue[0] == -60 && columns.residue[1] == -1, "a column reject leaves the sign-extended columns");
}

} // namespace

int main() {
  retailBoxIsTheGuestScreen();
  marginAdmitsTheWideColumns();
  rowsStayRetail();
  aQuadSpanningTheEdgeIsVisibleAtRetail();
  residueHoldsTheLastComparedValues();
  if (failures == 0) {
    std::puts("[PASS] vagrant_battle_cull");
  }
  return failures == 0 ? 0 : 1;
}
