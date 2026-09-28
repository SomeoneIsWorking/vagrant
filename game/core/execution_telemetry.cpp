#include "core/execution_telemetry.h"

#include <lucent/log.h>

#include <algorithm>

namespace vagrant {
namespace {

constexpr std::size_t kExitReasonCount = 8u;

std::size_t reasonIndex(psx::cpu::ExecutionExitReason reason) {
  return std::min(static_cast<std::size_t>(reason), kExitReasonCount - 1u);
}

} // namespace

std::uint64_t ExecutionTelemetry::OverrideHits::total() const {
  std::uint64_t sum = uncounted;
  for (std::size_t index = 0; index < entryCount; ++index) {
    sum += entries[index].calls;
  }
  return sum;
}

void ExecutionTelemetry::recordOverrideInstall(bool hadActiveImage, bool accepted) {
  ++overrideInstalls_.attempts;
  if (accepted) {
    ++overrideInstalls_.accepted;
    return;
  }
  if (hadActiveImage) {
    ++overrideInstalls_.refusedDispatcher;
  } else {
    ++overrideInstalls_.refusedNoActiveImage;
  }
}

void ExecutionTelemetry::recordOverrideHit(std::string_view name) {
  const auto found = std::find_if(
      overrideHits_.entries.begin(), overrideHits_.entries.begin() + static_cast<std::ptrdiff_t>(overrideHits_.entryCount),
      [name](const OverrideHits::Entry &entry) {
        return entry.name == name;
      });
  if (found != overrideHits_.entries.begin() + static_cast<std::ptrdiff_t>(overrideHits_.entryCount)) {
    ++found->calls;
    return;
  }
  if (overrideHits_.entryCount >= OverrideHits::kCapacity) {
    ++overrideHits_.uncounted;
    return;
  }
  overrideHits_.entries[overrideHits_.entryCount] = {.name = std::string(name), .calls = 1u};
  ++overrideHits_.entryCount;
}

void ExecutionTelemetry::recordExecutableWrite(std::uint64_t bytes, std::uint64_t overlappedBytes) {
  ++executableWrites_.candidates;
  executableWrites_.candidateBytes += bytes;
  if (overlappedBytes != 0u) {
    ++executableWrites_.residencyOverlaps;
    executableWrites_.overlapBytes += overlappedBytes;
  }
}

void ExecutionTelemetry::recordOriginalCall(psx::cpu::ExecutionExitReason reason) {
  ++originalCalls_.attempts;
  if (reason == psx::cpu::ExecutionExitReason::GuestReturn) {
    ++originalCalls_.returned;
  } else {
    ++originalCalls_.exitedEarly;
  }
}

void ExecutionTelemetry::recordDispatch(psx::cpu::ExecutionExitReason reason) {
  ++dispatches_.calls;
  ++dispatches_.exitsByReason[reasonIndex(reason)];
}

void ExecutionTelemetry::report(std::string_view owner) const {
  lucent::info(owner,
               "native overrides: {} install attempt(s) over {} owner(s) — accepted {}, refused {} "
               "({} with no unambiguous active image at the address, {} refused by the dispatcher); "
               "invocations {}",
               overrideInstalls_.attempts,
               overrideHits_.entryCount,
               overrideInstalls_.accepted,
               overrideInstalls_.refused(),
               overrideInstalls_.refusedNoActiveImage,
               overrideInstalls_.refusedDispatcher,
               overrideHits_.total());
  for (std::size_t index = 0; index < overrideHits_.entryCount; ++index) {
    lucent::info(owner, "  native override '{}' was invoked {} time(s)", overrideHits_.entries[index].name,
                 overrideHits_.entries[index].calls);
  }
  lucent::info(owner,
               "  override census capacity is {} of {} named owner(s); {} invocation(s) arrived after it "
               "was full and are counted in the total only",
               overrideHits_.entryCount,
               OverrideHits::kCapacity,
               overrideHits_.uncounted);
  lucent::info(owner,
               "executable writes: {} candidate notification(s) over {} byte(s); {} of them overlapped "
               "{} byte(s) a PREVIOUS authenticated image owned in the same address slot. Compared "
               "ranges, not Lightrec blocks: this owner does not count what the framework invalidated",
               executableWrites_.candidates,
               executableWrites_.candidateBytes,
               executableWrites_.residencyOverlaps,
               executableWrites_.overlapBytes);
  lucent::info(owner,
               "original calls: {} attempt(s) from native owners — {} returned to the owner, {} ended the "
               "call by another typed exit. Suppression DEPTH is not counted here: psxport's "
               "NativeDispatcher owns it and exposes no reading",
               originalCalls_.attempts,
               originalCalls_.returned,
               originalCalls_.exitedEarly);
  for (std::size_t index = 0; index < kExitReasonCount; ++index) {
    const auto reason = static_cast<psx::cpu::ExecutionExitReason>(index);
    lucent::info(owner,
                 "  guest dispatch exits by reason {}: {} of {} dispatch call(s)",
                 psx::cpu::executionExitName(reason),
                 dispatches_.exitsFor(reason),
                 dispatches_.calls);
  }
}

} // namespace vagrant
