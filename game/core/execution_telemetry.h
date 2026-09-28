#pragma once

#include "execution_exit.h"

#include <array>
#include <cstdint>
#include <string>
#include <string_view>

namespace vagrant {

// The execution boundaries THIS TITLE crosses, each recorded with the denominator that makes its
// zero readable. Two rules from the framework's diagnostics contract decide what belongs here:
//
//   * a count that could be zero because the instrument never ran is not a measurement, so every
//     counter below has an explicit `attempts`/`candidates` companion and the run-end report prints
//     both; and
//   * the report must name what was compared, so `residencyOverlaps` counts candidates that
//     overlapped bytes a PREVIOUS authenticated image owned in that address slot — not "blocks the
//     framework invalidated", which is a different question this title cannot answer.
//
// psxport's own executor counters (translated/executed blocks, cache hits/misses, invalidations and
// the per-reason interpreter-fallback counts) are deliberately NOT restated here. They are read once
// from `psx::cpu::LightrecExecutor::counters()` at run end, and a second copy of that table would be
// a second answer to a question that already has one owner.
class ExecutionTelemetry {
public:
  struct OverrideInstalls {
    std::uint64_t attempts = 0;
    std::uint64_t accepted = 0;
    std::uint64_t refusedNoActiveImage = 0;
    std::uint64_t refusedDispatcher = 0;

    [[nodiscard]] std::uint64_t refused() const {
      return refusedNoActiveImage + refusedDispatcher;
    }
  };

  struct OverrideHits {
    static constexpr std::size_t kCapacity = 16;

    struct Entry {
      std::string name;
      std::uint64_t calls = 0;
    };

    std::array<Entry, kCapacity> entries{};
    std::size_t entryCount = 0;
    // Named owners observed after the census was full. Without this, a dropped owner reads as an
    // owner that was never reached.
    std::uint64_t uncounted = 0;

    [[nodiscard]] std::uint64_t total() const;
  };

  struct ExecutableWrites {
    std::uint64_t candidates = 0;
    std::uint64_t candidateBytes = 0;
    std::uint64_t residencyOverlaps = 0;
    std::uint64_t overlapBytes = 0;
  };

  // One executable-write report's two extents, as ONE value rather than two adjacent integers.
  //
  // This was `recordExecutableWrite(std::uint64_t bytes, std::uint64_t overlappedBytes)`, and two
  // adjacent `std::uint64_t` parameters that mean "everything this write touched" and "the part of
  // it that collided with a previous image" are the pair a caller gets backwards without noticing:
  // the call still compiles, still runs, and reports a real-looking number. Naming the two roles
  // makes the swap unrepresentable, which is the whole point of the type.
  struct WriteExtents {
    std::uint64_t bytes = 0;           // the whole normalized range the write made visible
    std::uint64_t overlappedBytes = 0; // the subset that overlapped a PREVIOUS authenticated image
  };

  struct OriginalCalls {
    std::uint64_t attempts = 0;
    std::uint64_t returned = 0;
    std::uint64_t exitedEarly = 0;
  };

  struct Dispatches {
    std::uint64_t calls = 0;
    // Indexed by `static_cast<std::size_t>(psx::cpu::ExecutionExitReason)`, whose enumeration has
    // exactly these values. Named readers should prefer `exitsFor`, which is a total function over
    // the reason rather than a raw subscript a caller can read past.
    std::array<std::uint64_t, 8> exitsByReason{};

    [[nodiscard]] std::uint64_t exitsFor(psx::cpu::ExecutionExitReason reason) const {
      return exitsByReason[static_cast<std::size_t>(reason)];
    }
  };

  void recordOverrideInstall(bool hadActiveImage, bool accepted);
  void recordOverrideHit(std::string_view name);
  void recordExecutableWrite(WriteExtents extents);
  void recordOriginalCall(psx::cpu::ExecutionExitReason reason);
  void recordDispatch(psx::cpu::ExecutionExitReason reason);

  [[nodiscard]] const OverrideInstalls &overrideInstalls() const {
    return overrideInstalls_;
  }
  [[nodiscard]] const OverrideHits &overrideHits() const {
    return overrideHits_;
  }
  [[nodiscard]] const ExecutableWrites &executableWrites() const {
    return executableWrites_;
  }
  [[nodiscard]] const OriginalCalls &originalCalls() const {
    return originalCalls_;
  }
  [[nodiscard]] const Dispatches &dispatches() const {
    return dispatches_;
  }

  // One report block per owner, each line carrying its own denominator. `owner` is the log domain.
  // The line also states which denominators this owner does NOT hold, so a reader never has to guess
  // whether a missing number means "none happened" or "nobody counts that here".
  void report(std::string_view owner) const;

private:
  OverrideInstalls overrideInstalls_{};
  OverrideHits overrideHits_{};
  ExecutableWrites executableWrites_{};
  OriginalCalls originalCalls_{};
  Dispatches dispatches_{};
};

} // namespace vagrant
