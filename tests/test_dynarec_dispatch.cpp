// The title's adapter surface over psxport's dynarec executor, exercised through the SHIPPING seam.
//
// What this test is for. `vagrant::dynarec` is the whole title/dynarec boundary, and three of its five
// operations can fail silently in ways a boot log would not distinguish from success:
//
//   * an override installed against the wrong image generation, which would attribute a resident leaf
//     to an overlay's bytes — the exact hazard this title has, because BATTLE, TITLE and ENDING all
//     load at 0x80068800;
//   * a `callOriginal` that did not suppress only its own key, so a native owner re-entering the
//     guest would recurse into itself; and
//   * telemetry whose zeros are indistinguishable from "the instrument never ran".
//
// Every case below is a NEGATIVE whose absence of evidence would otherwise read as a pass. The
// positive case is that a real translated block executes and returns its guest result.

#include "core.h"
#include "core/dynarec_dispatch.h"
#include "core/execution_telemetry.h"
#include "core/game_heap.h"
#include "core/overlay_images.h"
#include "core/resident_image.h"
#include "core/vagrant_context.h"
#include "game.h"
#include "lightrec_executor.h"
#include "lucent/content.h"
#include "vagrant_runtime.h"

#include "core/resident_facts.h"

#include <array>
#include <cstdint>
#include <cstdio>
#include <memory>
#include <span>
#include <string>
#include <vector>

namespace {

int g_failures = 0;

void require(bool condition, const char *subject, const char *message) {
  if (condition) {
    return;
  }
  ++g_failures;
  std::fprintf(stderr, "FAIL [%s] %s\n", subject, message);
}

void writeWord(std::vector<std::uint8_t> &bytes, std::size_t offset, std::uint32_t value) {
  for (unsigned byte = 0; byte < 4; ++byte) {
    bytes[offset + byte] = static_cast<std::uint8_t>(value >> (byte * 8));
  }
}

// A minimal but REAL PS-X EXE: the measured header, a measured-shape text extent, and real MIPS
// instructions at a real entry. `addiu v0, zero, VALUE / jr ra / nop` returns VALUE in v0, so a
// caller can tell execution from a refusal by reading a guest register afterwards.
std::vector<std::uint8_t> residentFixture(std::uint32_t resultValue) {
  std::vector<std::uint8_t> bytes(0x800u + vagrant::kResidentHeader.textBytes, 0u);
  constexpr std::array<std::uint8_t, 8> magic{'P', 'S', '-', 'X', ' ', 'E', 'X', 'E'};
  std::copy(magic.begin(), magic.end(), bytes.begin());
  writeWord(bytes, 0x10u, vagrant::kResidentHeader.entry);
  writeWord(bytes, 0x14u, vagrant::kResidentHeader.globalPointer);
  writeWord(bytes, 0x18u, vagrant::kResidentHeader.textAddress);
  writeWord(bytes, 0x1Cu, vagrant::kResidentHeader.textBytes);
  writeWord(bytes, 0x30u, vagrant::kResidentHeader.stackBase);
  writeWord(bytes, 0x34u, vagrant::kResidentHeader.stackOffset);
  const auto entryOffset = 0x800u + vagrant::kResidentHeader.entry - vagrant::kResidentHeader.textAddress;
  writeWord(bytes, entryOffset, 0x24020000u | resultValue);
  writeWord(bytes, entryOffset + 4u, 0x03E00008u);
  // A second function further up the image, so an original call has a body that is not the entry.
  const auto leafOffset = 0x800u + vagrant::kResidentHeader.textAddress + 0x100u - vagrant::kResidentHeader.textAddress;
  writeWord(bytes, leafOffset, 0x24020000u | (resultValue ^ 0x5A5Au));
  writeWord(bytes, leafOffset + 4u, 0x03E00008u);
  return bytes;
}

// The overlay image bytes: same shape, deliberately not a retail PRG, so a publication is a
// measurable event without claiming to be the real TITLE image. The bytes are zero so the fixture
// never shadows real code.
std::vector<std::uint8_t> overlayFixture() {
  return std::vector<std::uint8_t>(0x100u, 0u);
}

std::string sha256Of(const std::vector<std::uint8_t> &bytes) {
  return lucent::content::sha256_hex(
      lucent::content::sha256({reinterpret_cast<const std::byte *>(bytes.data()), bytes.size()}));
}

void nativeLeaf(Core *) {
}

void observeHits(Core *core) {
  vagrant::contextOf(*core).executionTelemetry.recordOverrideHit("test owner");
}

struct Machine {
  std::unique_ptr<vagrant::VagrantRuntime> runtime;
  std::unique_ptr<Game> game;
  Core &core() {
    return game->core;
  }
};

// `ImageIdentity` has a default member initialiser, so `x == y` is NOT an aggregate comparison in
// C++20 and the common-type conversion from the optional never happens. This helper is the one
// reading of "is this address owned by that exact generation", used by every case below so a
// retired generation and an absent one cannot be confused.
bool ownedBy(const Core &core, std::uint32_t address, psx::cpu::ImageIdentity image) {
  return core.currentImageIdentity(address) == image;
}

std::unique_ptr<Machine> makeMachine(const std::vector<std::uint8_t> &resident) {
  auto machine = std::make_unique<Machine>();
  machine->runtime = std::make_unique<vagrant::VagrantRuntime>();
  psxport_install_game(*machine->runtime);
  machine->game = std::make_unique<Game>();
  return machine;
}

// 1. The positive case, and the zero-fallback claim: a real translated block executes and returns
//    the guest's own result. A refusal that also leaves v0 untouched must be distinguishable, which
//    is why the value is checked rather than merely "no crash".
void executesRealGuestCode() {
  const auto bytes = residentFixture(0x2Du);
  auto machine = makeMachine(bytes);
  Core &core = machine->core();
  const auto loaded = machine->runtime->loadResidentImage(core, bytes, vagrant::kResidentImageName);
  require(static_cast<bool>(loaded), "execute", "the measured resident image was refused");
  if (!loaded) {
    return;
  }
  const auto &before = core.lightrecExecutor().counters();
  const std::uint64_t callsBefore = before.calls;
  const std::uint64_t blocksBefore = before.executedBlocks;
  core.r[2] = 0u;
  const auto result = vagrant::dynarec::callGuest(core, vagrant::kResidentHeader.entry);
  const auto &after = core.lightrecExecutor().counters();
  require(result.reason == psx::cpu::ExecutionExitReason::GuestReturn, "execute", "the entry call did not return");
  require(core.r[2] == 0x2Du, "execute", "the guest result register does not hold the executed value");
  require(after.calls == callsBefore + 1u, "execute", "the executor call counter did not advance once");
  require(after.executedBlocks > blocksBefore, "execute", "no translated block was executed");
  require(after.fallback.calls == 0u, "execute", "a block was interpreted rather than translated");
}

// 2. `callGuest` must accept a bounded turn and report the typed reason, so a caller that expected a
//    finite leaf can tell a finished call from an exhausted budget. A loop that never returns is the
//    negative: the exit reason is what stops it.
void reportsTypedExitOnBudgetExhaustion() {
  // `b .` with nothing that can return: the entry is an infinite self-branch, so only the bounded
  // budget can end the turn. The image is still a valid PS-X EXE, so what is under test is the
  // budget and the typed reason, not image admission.
  auto bytes = residentFixture(1u);
  const auto entryOffset = 0x800u + vagrant::kResidentHeader.entry - vagrant::kResidentHeader.textAddress;
  writeWord(bytes, entryOffset, 0x1000FFFFu);      // beq $zero,$zero,-1 : branch to itself
  writeWord(bytes, entryOffset + 4u, 0x00000000u); // delay slot: nop
  auto machine = makeMachine(bytes);
  Core &core = machine->core();
  const auto loaded = machine->runtime->loadResidentImage(core, bytes, vagrant::kResidentImageName);
  require(static_cast<bool>(loaded), "typed-exit", "the loop fixture was refused as an image");
  if (!loaded) {
    return;
  }
  const auto result = vagrant::dynarec::executeTurn(core, vagrant::kResidentHeader.entry);
  require(result.reason == psx::cpu::ExecutionExitReason::BudgetExhausted,
          "typed-exit",
          "an unbounded guest loop did not end in BudgetExhausted");
  // The exit PC must be INSIDE the loop the caller asked to bound. Asserting equality with the
  // entry would be wrong: Lightrec exits at a translated block boundary, so the reported PC is a
  // legitimate second instruction of the same loop. The claim under test is "it stopped where it
  // was running", and a PC anywhere else — including the entry, coincidentally — would be the
  // distinction this cannot make.
  require(result.guestPc >= vagrant::kResidentHeader.entry && result.guestPc < vagrant::kResidentHeader.entry + 0x10u,
          "typed-exit",
          "the reported exit PC is not inside the loop the caller asked to bound");
  require(result.cycles > 0u, "typed-exit", "an exhausted budget reported zero consumed cycles");
}

// 3. THE hazard this title has. An override must refuse an address that resolves to no active image,
//    and must refuse one that resolves to a DIFFERENT generation than the caller published. Both
//    refusals are counted, so a run that installed nothing cannot report the same numbers as a run
//    that never tried — the failure this workspace has measured five times in four titles.
void refusesUnscopedAndStaleGenerations() {
  const auto bytes = residentFixture(7u);
  auto machine = makeMachine(bytes);
  Core &core = machine->core();
  auto &telemetry = vagrant::contextOf(core).executionTelemetry;

  // (a) Before any image is published there is no image to attribute a leaf to.
  const std::uint64_t attemptsBeforeUnscoped = telemetry.overrideInstalls().attempts;
  const bool unscoped = vagrant::dynarec::installNativeOverride(core, 0x80010200u, "unscoped owner", nativeLeaf);
  require(!unscoped, "generation", "an override was installed with no active image at the address");
  require(telemetry.overrideInstalls().attempts == attemptsBeforeUnscoped + 1u,
          "generation",
          "the refused install was not counted as an attempt");
  require(telemetry.overrideInstalls().refusedNoActiveImage == 1u,
          "generation",
          "the no-image refusal was not attributed to its own reason");

  const auto loaded = machine->runtime->loadResidentImage(core, bytes, vagrant::kResidentImageName);
  require(static_cast<bool>(loaded), "generation", "the measured resident image was refused");
  if (!loaded) {
    return;
  }
  const psx::cpu::ImageIdentity resident = loaded.identity.value();

  // (b) A caller that names the wrong generation must be refused even though the address resolves.
  const auto wrongGeneration = psx::cpu::ImageIdentity{resident.id, resident.generation + 1u};
  const std::uint64_t acceptedBefore = telemetry.overrideInstalls().accepted;
  require(!vagrant::dynarec::installNativeOverride(core, 0x80010100u, "stale owner", nativeLeaf, wrongGeneration),
          "generation",
          "an override was installed against a generation the caller did not publish");
  require(telemetry.overrideInstalls().accepted == acceptedBefore,
          "generation",
          "the generation refusal was counted as an accepted install");

  // (c) The matching generation installs, and the leaf is then REACHABLE through that key.
  const std::uint32_t owned = 0x80010100u;
  require(vagrant::dynarec::installNativeOverride(core, owned, "owned owner", observeHits, resident),
          "generation",
          "the correctly scoped override was refused");
  require(vagrant::dynarec::hasNativeOverride(core, resident, owned),
          "generation",
          "the installed override is not reachable through its own key");
  require(!vagrant::dynarec::hasNativeOverride(core, wrongGeneration, owned),
          "generation",
          "a retired generation reached an override it never owned");

  // (d) A null handler is refused rather than installed as a callable key.
  require(!vagrant::dynarec::installNativeOverride(core, 0x80010104u, "null owner", nullptr, resident),
          "generation",
          "an override with no handler was installed");

  // (e) A SECOND registration of the same key must be refused BY THE DISPATCHER, and that refusal must
  //     be counted as a dispatcher refusal rather than silently folded into the accepted total. This
  //     case exists because the previous version of this test could not produce a dispatcher refusal
  //     at all, which left `refusedDispatcher` a counter no test reached — the exact shape of a
  //     denominator nobody has seen fire.
  const std::uint64_t dispatcherRefusalsBefore = telemetry.overrideInstalls().refusedDispatcher;
  const std::uint64_t acceptedBeforeDuplicate = telemetry.overrideInstalls().accepted;
  require(!vagrant::dynarec::installNativeOverride(core, owned, "duplicate owner", observeHits, resident),
          "generation",
          "a duplicate registration of the same key was accepted");
  require(telemetry.overrideInstalls().refusedDispatcher == dispatcherRefusalsBefore + 1u,
          "generation",
          "the dispatcher's refusal was not counted as a dispatcher refusal");
  require(telemetry.overrideInstalls().accepted == acceptedBeforeDuplicate,
          "generation",
          "a refused duplicate registration was counted as accepted");
  require(vagrant::dynarec::hasNativeOverride(core, resident, owned),
          "generation",
          "the refused duplicate registration displaced the original owner");
}

// 4. `callOriginal` must suppress ONLY the key it names, for one call. The proof is that the native
//    leaf's own re-entry reaches the guest body and RETURNS, instead of recursing into itself, and
//    that the guest's own result is what comes back.
void originalCallReachesTheGuestBody() {
  const auto bytes = residentFixture(0x11u);
  auto machine = makeMachine(bytes);
  Core &core = machine->core();
  const auto loaded = machine->runtime->loadResidentImage(core, bytes, vagrant::kResidentImageName);
  require(static_cast<bool>(loaded), "original", "the measured resident image was refused");
  if (!loaded) {
    return;
  }
  const psx::cpu::ImageIdentity resident = loaded.identity.value();
  constexpr std::uint32_t kLeaf = 0x80010100u;
  constexpr std::uint32_t kLeafResult = 0x11u ^ 0x5A5Au;

  // The leaf's own body is the fixture's second function. Installing the override here, then
  // re-entering the original, must land on the GUEST value, not on the native handler.
  require(vagrant::dynarec::installNativeOverride(core, kLeaf, "original-suppressed owner", nativeLeaf, resident),
          "original",
          "the scoped override was refused");
  auto &telemetry = vagrant::contextOf(core).executionTelemetry;
  const std::uint64_t originalCallsBefore = telemetry.originalCalls().attempts;

  // BOTH overloads are exercised. The address form and the `NativeKey` form are separate code paths,
  // and testing only one left the other unreached — which is how a suppression bug in the untested
  // one would have read as a green suite.
  for (const bool byKey : {false, true}) {
    const std::string which = byKey ? "NativeKey" : "address";
    core.r[31] = 0x80010200u;
    core.r[2] = 0u;
    const auto result = byKey ? vagrant::dynarec::callOriginal(core, psx::cpu::NativeKey{resident, kLeaf})
                              : vagrant::dynarec::callOriginal(core, kLeaf);
    require(result.reason == psx::cpu::ExecutionExitReason::GuestReturn,
            "original",
            (std::string("the original call by ") + which + " did not return through the guest body").c_str());
    require(core.r[2] == kLeafResult,
            "original",
            (std::string("the original call by ") + which +
             " returned a value the guest body does not produce, so suppression did not work")
                .c_str());
  }
  require(telemetry.originalCalls().attempts == originalCallsBefore + 2u,
          "original",
          "the original-call attempts were not counted, so a suppressed call would read as a normal one");

  // The native handler must NOT have run: it is a no-op, so running it would leave v0 at 0 rather
  // than the guest's own result. That is asserted above by VALUE, not by a separate flag, so a
  // native handler that happened to write v0 could not pass by coincidence.
  require(core.lightrecExecutor().counters().executedBlocks > 0u,
          "original",
          "the original call executed no translated block");
}

// 5. The telemetry's arithmetic must close, and its zeros must be attributable. The census is only
//    evidence if every attempt lands in exactly one bucket, and if a name that was never hit is
//    distinguishable from one that was.
void telemetryDenominatorsClose() {
  vagrant::ExecutionTelemetry telemetry;
  require(telemetry.overrideInstalls().attempts == 0u, "telemetry", "a fresh census reported attempts");
  require(telemetry.overrideHits().total() == 0u, "telemetry", "a fresh census reported override hits");
  require(telemetry.dispatches().calls == 0u, "telemetry", "a fresh census reported dispatches");

  telemetry.recordOverrideInstall(false, false);
  telemetry.recordOverrideInstall(true, false);
  telemetry.recordOverrideInstall(true, true);
  const auto &installs = telemetry.overrideInstalls();
  require(installs.attempts == 3u, "telemetry", "the install attempts were not counted");
  require(installs.accepted == 1u, "telemetry", "the accepted install was not counted");
  require(installs.refusedNoActiveImage == 1u, "telemetry", "the no-image refusal was misattributed");
  require(installs.refusedDispatcher == 1u, "telemetry", "the dispatcher refusal was misattributed");
  require(installs.accepted + installs.refused() == installs.attempts,
          "telemetry",
          "the install census does not close: accepted + refused != attempts");

  telemetry.recordOverrideHit("a");
  telemetry.recordOverrideHit("a");
  telemetry.recordOverrideHit("b");
  require(telemetry.overrideHits().total() == 3u, "telemetry", "repeated hits on one owner were not accumulated");
  require(telemetry.overrideHits().entryCount == 2u, "telemetry", "two distinct owners produced three census rows");

  // A census with capacity is not a census that can be trusted once it fills. Past the capacity the
  // total must still grow, or a run with 40 distinct owners would report 16 and read as complete.
  for (std::size_t index = 0; index < vagrant::ExecutionTelemetry::OverrideHits::kCapacity + 4u; ++index) {
    telemetry.recordOverrideHit("filler" + std::to_string(index));
  }
  require(telemetry.overrideHits().entryCount == vagrant::ExecutionTelemetry::OverrideHits::kCapacity,
          "telemetry",
          "the override census grew past its declared capacity");
  require(telemetry.overrideHits().uncounted > 0u,
          "telemetry",
          "invocations past the census capacity were dropped without saying so");

  telemetry.recordExecutableWrite(0x87800u, 0x87800u);
  telemetry.recordExecutableWrite(0x100u, 0u);
  require(telemetry.executableWrites().candidates == 2u, "telemetry", "the write candidates were not counted");
  require(telemetry.executableWrites().residencyOverlaps == 1u,
          "telemetry",
          "a write that overlapped a prior generation was not counted as one");
  require(telemetry.executableWrites().candidateBytes == 0x87900u, "telemetry", "the candidate byte total is wrong");

  telemetry.recordOriginalCall(psx::cpu::ExecutionExitReason::GuestReturn);
  telemetry.recordOriginalCall(psx::cpu::ExecutionExitReason::BudgetExhausted);
  require(telemetry.originalCalls().attempts == 2u, "telemetry", "the original-call attempts were not counted");
  require(telemetry.originalCalls().returned == 1u, "telemetry", "a returned original call was not counted");
  require(telemetry.originalCalls().exitedEarly == 1u, "telemetry", "an early-exited original call was not counted");

  telemetry.recordDispatch(psx::cpu::ExecutionExitReason::GuestReturn);
  telemetry.recordDispatch(psx::cpu::ExecutionExitReason::Fault);
  const auto exitsFor = [&telemetry](psx::cpu::ExecutionExitReason reason) {
    return telemetry.dispatches().exitsFor(reason);
  };
  require(telemetry.dispatches().calls == 2u, "telemetry", "the dispatch calls were not counted");
  require(exitsFor(psx::cpu::ExecutionExitReason::GuestReturn) == 1u,
          "telemetry",
          "the guest-return exit was not attributed to its own reason");
  require(exitsFor(psx::cpu::ExecutionExitReason::Fault) == 1u,
          "telemetry",
          "the fault exit was not attributed to its own reason");
  require(exitsFor(psx::cpu::ExecutionExitReason::BudgetExhausted) == 0u,
          "telemetry",
          "a reason with no exits reported one, so the census cannot be read as scanned");
}

// 6. The shipping heap leaf must be reachable through the title's own registry and must be keyed to
//    the resident generation. This is the one native body S007 already verified byte-for-byte, and it
//    is the first leaf the adapter made reachable at all.
void registersTheMeasuredHeapLeaf() {
  const auto bytes = residentFixture(0u);
  auto machine = makeMachine(bytes);
  Core &core = machine->core();
  const auto loaded = machine->runtime->loadResidentImage(core, bytes, vagrant::kResidentImageName);
  require(static_cast<bool>(loaded), "heap-leaf", "the measured resident image was refused");
  if (!loaded) {
    return;
  }
  const psx::cpu::ImageIdentity resident = loaded.identity.value();
  require(vagrant::dynarec::hasNativeOverride(core, resident, vagrant::heap::kInitHeap),
          "heap-leaf",
          "vs_main_initHeap is not owned on the resident generation the load published");
  require(!vagrant::dynarec::hasNativeOverride(core, {resident.id, resident.generation + 1u}, vagrant::heap::kInitHeap),
          "heap-leaf",
          "vs_main_initHeap is reachable through a generation that was never published");
}

// 7. Overlay-to-overlay generation replacement must retire the previous generation's override keys.
//    This is the hazard the framework's image-scoped rule exists for, and it is REAL in this title
//    because BATTLE, TITLE and ENDING all load at 0x80068800 — the overlays reuse EACH OTHER's
//    range. (They do NOT reuse the resident's: the resident text ends at 0x80062000, and an
//    instrument that claimed otherwise would be reporting a hazard the bytes contradict.)
//    The negative: an override owned by the retired TITLE generation must become unreachable, while
//    the resident generation's own leaf must survive, because its range is genuinely disjoint.
void overlayReplacementRetiresThePriorGenerationsKeys() {
  const auto bytes = residentFixture(0u);
  auto machine = makeMachine(bytes);
  Core &core = machine->core();
  const auto loaded = machine->runtime->loadResidentImage(core, bytes, vagrant::kResidentImageName);
  require(static_cast<bool>(loaded), "overlay-retire", "the measured resident image was refused");
  if (!loaded) {
    return;
  }
  const psx::cpu::ImageIdentity resident = loaded.identity.value();
  require(vagrant::dynarec::hasNativeOverride(core, resident, vagrant::heap::kInitHeap),
          "overlay-retire",
          "the resident heap leaf was not owned before the overlay load");

  const auto titleBytes = overlayFixture();
  auto battleBytes = overlayFixture();
  battleBytes[0] = 0x24u; // a DIFFERENT image, so the replacement is a real content change
  const std::array<vagrant::OverlaySpec, 3> specs{{
      {vagrant::OverlayKind::Title,
       "TITLE.PRG",
       vagrant::resident::kTitleOverlayBase,
       titleBytes.size(),
       sha256Of(titleBytes)},
      {vagrant::OverlayKind::Battle,
       "BATTLE.PRG",
       vagrant::resident::kTitleOverlayBase,
       battleBytes.size(),
       sha256Of(battleBytes)},
      {vagrant::OverlayKind::InitBattle, "INITBTL.PRG", 0x800F9800u, 4u, sha256Of(battleBytes)},
  }};
  vagrant::OverlayImages overlays(core, specs);

  const auto title = overlays.load(vagrant::OverlayKind::Title, titleBytes);
  require(static_cast<bool>(title), "overlay-retire", "the synthetic TITLE image was refused");
  if (!title) {
    return;
  }
  constexpr std::uint32_t kOverlayEntry = vagrant::resident::kTitleOverlayBase;
  require(vagrant::dynarec::installNativeOverride(
              core, kOverlayEntry, "TITLE-owned leaf", nativeLeaf, title.identity.value()),
          "overlay-retire",
          "a leaf scoped to the TITLE generation was refused");
  require(vagrant::dynarec::hasNativeOverride(core, title.identity.value(), kOverlayEntry),
          "overlay-retire",
          "the TITLE-scoped leaf is not reachable through its own generation");

  const auto battle = overlays.load(vagrant::OverlayKind::Battle, battleBytes);
  require(static_cast<bool>(battle), "overlay-retire", "the BATTLE replacement was refused");
  if (!battle) {
    return;
  }
  require(ownedBy(core, kOverlayEntry, battle.identity.value()),
          "overlay-retire",
          "the BATTLE publication did not become the active generation at 0x80068800");
  require(!vagrant::dynarec::hasNativeOverride(core, title.identity.value(), kOverlayEntry),
          "overlay-retire",
          "a TITLE-generation override survived the BATTLE publication that reused its address slot");
  require(vagrant::dynarec::hasNativeOverride(core, resident, vagrant::heap::kInitHeap),
          "overlay-retire",
          "the resident generation's own leaf was retired by an overlay load, but the resident text ends "
          "at 0x80062000 and the overlay base is 0x80068800, so those ranges are disjoint");
}

} // namespace

int main() {
  executesRealGuestCode();
  reportsTypedExitOnBudgetExhaustion();
  refusesUnscopedAndStaleGenerations();
  originalCallReachesTheGuestBody();
  telemetryDenominatorsClose();
  registersTheMeasuredHeapLeaf();
  overlayReplacementRetiresThePriorGenerationsKeys();
  if (g_failures != 0) {
    std::fprintf(stderr, "dynarec dispatch contract: %d failure(s)\n", g_failures);
    return 1;
  }
  std::printf("dynarec dispatch contract: 7/7 groups passed\n");
  return 0;
}
