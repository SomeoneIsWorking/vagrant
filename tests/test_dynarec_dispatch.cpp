// Title adapter over psxport's dynarec executor, through the shipping seam.

#include "boot/game_heap.h"
#include "boot/resident_image.h"
#include "cd/cd_facts.h"
#include "core.h"
#include "execution/dynarec_dispatch.h"
#include "game.h"
#include "images/overlay_images.h"
#include "lightrec_executor.h"
#include "lucent/content.h"
#include "runtime/vagrant_context.h"
#include "runtime/vagrant_runtime.h"

#include "boot/resident_facts.h"

#include <array>
#include <cstdint>
#include <cstdio>
#include <exception>
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

// The generation one completed load published, checked rather than assumed.
psx::cpu::ImageIdentity identityOf(const psx::cpu::PsxExeLoadResult &loaded, const char *subject) {
  if (!loaded.identity) {
    std::fprintf(stderr, "FAIL [%s] a completed load published no image generation\n", subject);
    ++g_failures;
  }
  return loaded.identity.value_or(psx::cpu::ImageIdentity{});
}

// A completed overlay load's generation.
psx::cpu::ImageIdentity identityOf(const vagrant::OverlayLoadResult &loaded, const char *subject) {
  if (!loaded.identity) {
    std::fprintf(stderr, "FAIL [%s] a completed overlay load published no image generation\n", subject);
    ++g_failures;
  }
  return loaded.identity.value_or(psx::cpu::ImageIdentity{});
}

void writeWord(std::vector<std::uint8_t> &bytes, std::size_t offset, std::uint32_t value) {
  for (unsigned byte = 0; byte < 4; ++byte) {
    bytes[offset + byte] = static_cast<std::uint8_t>(value >> (byte * 8));
  }
}

// Minimal PS-X EXE: `addiu v0, zero, VALUE / jr ra / nop` returns VALUE in v0.
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
  // A second function so an original call has a body that is not the entry.
  const auto leafOffset = 0x800u + vagrant::kResidentHeader.textAddress + 0x100u - vagrant::kResidentHeader.textAddress;
  writeWord(bytes, leafOffset, 0x24020000u | (resultValue ^ 0x5A5Au));
  writeWord(bytes, leafOffset + 4u, 0x03E00008u);
  return bytes;
}

// Overlay image bytes: not a retail PRG, zero-filled so it never shadows real code.
std::vector<std::uint8_t> overlayFixture() {
  return std::vector<std::uint8_t>(0x100u, 0u);
}

std::string sha256Of(const std::vector<std::uint8_t> &bytes) {
  return lucent::content::sha256_hex(
      lucent::content::sha256({reinterpret_cast<const std::byte *>(bytes.data()), bytes.size()}));
}

void nativeLeaf(Core *) {
}

struct Machine {
  std::unique_ptr<vagrant::VagrantRuntime> runtime;
  std::unique_ptr<Game> game;
  Core &core() {
    return game->core;
  }
};

// `ImageIdentity` has a default member initialiser, so `==` on the optional is not an aggregate comparison.
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

// 1. A real translated block executes and returns the guest's own result.
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

// 2. `callGuest` reports a typed exit reason on an exhausted budget.
void reportsTypedExitOnBudgetExhaustion() {
  // Infinite self-branch: only the budget can end the turn.
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
  // Lightrec exits at a block boundary, so the exit PC is anywhere inside the loop, not necessarily the entry.
  require(result.guestPc >= vagrant::kResidentHeader.entry && result.guestPc < vagrant::kResidentHeader.entry + 0x10u,
          "typed-exit",
          "the reported exit PC is not inside the loop the caller asked to bound");
  require(result.cycles > 0u, "typed-exit", "an exhausted budget reported zero consumed cycles");
}

// 3. An override is refused for an address with no active image or a different generation.
void refusesUnscopedAndStaleGenerations() {
  const auto bytes = residentFixture(7u);
  auto machine = makeMachine(bytes);
  Core &core = machine->core();

  // (a) Before any image is published there is no image to attribute a leaf to.
  const bool unscoped = vagrant::dynarec::installNativeOverride(core, 0x80010200u, "unscoped owner", nativeLeaf);
  require(!unscoped, "generation", "an override was installed with no active image at the address");

  const auto loaded = machine->runtime->loadResidentImage(core, bytes, vagrant::kResidentImageName);
  require(static_cast<bool>(loaded), "generation", "the measured resident image was refused");
  if (!loaded) {
    return;
  }
  const psx::cpu::ImageIdentity resident = identityOf(loaded, "generation");

  // (b) A caller that names the wrong generation must be refused even though the address resolves.
  const auto wrongGeneration = psx::cpu::ImageIdentity{resident.id, resident.generation + 1u};
  require(!vagrant::dynarec::installNativeOverride(core, 0x80010100u, "stale owner", nativeLeaf, wrongGeneration),
          "generation",
          "an override was installed against a generation the caller did not publish");

  // (c) The matching generation installs, and the leaf is then REACHABLE through that key.
  const std::uint32_t owned = 0x80010100u;
  require(vagrant::dynarec::installNativeOverride(core, owned, "owned owner", nativeLeaf, resident),
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

  // (e) A SECOND registration of the same key must be refused BY THE DISPATCHER.
  require(!vagrant::dynarec::installNativeOverride(core, owned, "duplicate owner", nativeLeaf, resident),
          "generation",
          "a duplicate registration of the same key was accepted");
  require(vagrant::dynarec::hasNativeOverride(core, resident, owned),
          "generation",
          "the refused duplicate registration displaced the original owner");
}

// 4. `callOriginal` suppresses only the key it names, for one call.
void originalCallReachesTheGuestBody() {
  const auto bytes = residentFixture(0x11u);
  auto machine = makeMachine(bytes);
  Core &core = machine->core();
  const auto loaded = machine->runtime->loadResidentImage(core, bytes, vagrant::kResidentImageName);
  require(static_cast<bool>(loaded), "original", "the measured resident image was refused");
  if (!loaded) {
    return;
  }
  const psx::cpu::ImageIdentity resident = identityOf(loaded, "original");
  constexpr std::uint32_t kLeaf = 0x80010100u;
  constexpr std::uint32_t kLeafResult = 0x11u ^ 0x5A5Au;

  // The leaf's own body is the fixture's second function; re-entry must land on the guest value.
  require(vagrant::dynarec::installNativeOverride(core, kLeaf, "original-suppressed owner", nativeLeaf, resident),
          "original",
          "the scoped override was refused");

  // Both overloads (address and `NativeKey`) are separate paths.
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

  // The native handler is a no-op, so running it would leave v0 at 0.
  require(core.lightrecExecutor().counters().executedBlocks > 0u,
          "original",
          "the original call executed no translated block");
}

// 6. The heap leaf is reachable through the title registry, keyed to the resident generation.
void registersTheMeasuredHeapLeaf() {
  const auto bytes = residentFixture(0u);
  auto machine = makeMachine(bytes);
  Core &core = machine->core();
  const auto loaded = machine->runtime->loadResidentImage(core, bytes, vagrant::kResidentImageName);
  require(static_cast<bool>(loaded), "heap-leaf", "the measured resident image was refused");
  if (!loaded) {
    return;
  }
  const psx::cpu::ImageIdentity resident = identityOf(loaded, "heap-leaf");
  require(vagrant::dynarec::hasNativeOverride(core, resident, vagrant::heap::kInitHeap),
          "heap-leaf",
          "vs_main_initHeap is not owned on the resident generation the load published");
  require(!vagrant::dynarec::hasNativeOverride(core, {resident.id, resident.generation + 1u}, vagrant::heap::kInitHeap),
          "heap-leaf",
          "vs_main_initHeap is reachable through a generation that was never published");
}

// 6b. Every leaf `installResidentNativeOwners` claims must be bound; an unbound `handleDsControlB` hung libcd `CD_sync`
// (0x80020F28).
void everyClaimedResidentLeafIsBound() {
  const auto bytes = residentFixture(0u);
  auto machine = makeMachine(bytes);
  Core &core = machine->core();
  const auto loaded = machine->runtime->loadResidentImage(core, bytes, vagrant::kResidentImageName);
  require(static_cast<bool>(loaded), "bound-leaves", "the measured resident image was refused");
  if (!loaded) {
    return;
  }
  const psx::cpu::ImageIdentity resident = identityOf(loaded, "bound-leaves");
  for (const std::uint32_t leaf : {vagrant::heap::kInitHeap, vagrant::cd::kDsControlB}) {
    require(vagrant::dynarec::hasNativeOverride(core, resident, leaf),
            "bound-leaves",
            "a leaf the resident registry claims is not reachable on the generation it published");
    require(!vagrant::dynarec::hasNativeOverride(core, {resident.id, resident.generation + 1u}, leaf),
            "bound-leaves",
            "a resident leaf is reachable through a generation that was never published");
  }
}

// 7. Replacing an overlay generation retires its override keys; the resident leaf survives (its range is disjoint).
void overlayReplacementRetiresThePriorGenerationsKeys() {
  const auto bytes = residentFixture(0u);
  auto machine = makeMachine(bytes);
  Core &core = machine->core();
  const auto loaded = machine->runtime->loadResidentImage(core, bytes, vagrant::kResidentImageName);
  require(static_cast<bool>(loaded), "overlay-retire", "the measured resident image was refused");
  if (!loaded) {
    return;
  }
  const psx::cpu::ImageIdentity resident = identityOf(loaded, "overlay-retire");
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
              core, kOverlayEntry, "TITLE-owned leaf", nativeLeaf, identityOf(title, "overlay-retire")),
          "overlay-retire",
          "a leaf scoped to the TITLE generation was refused");
  require(vagrant::dynarec::hasNativeOverride(core, identityOf(title, "overlay-retire"), kOverlayEntry),
          "overlay-retire",
          "the TITLE-scoped leaf is not reachable through its own generation");

  const auto battle = overlays.load(vagrant::OverlayKind::Battle, battleBytes);
  require(static_cast<bool>(battle), "overlay-retire", "the BATTLE replacement was refused");
  if (!battle) {
    return;
  }
  require(ownedBy(core, kOverlayEntry, identityOf(battle, "overlay-retire")),
          "overlay-retire",
          "the BATTLE publication did not become the active generation at 0x80068800");
  require(!vagrant::dynarec::hasNativeOverride(core, identityOf(title, "overlay-retire"), kOverlayEntry),
          "overlay-retire",
          "a TITLE-generation override survived the BATTLE publication that reused its address slot");
  require(vagrant::dynarec::hasNativeOverride(core, resident, vagrant::heap::kInitHeap),
          "overlay-retire",
          "the resident generation's own leaf was retired by an overlay load, but the resident text ends "
          "at 0x80062000 and the overlay base is 0x80068800, so those ranges are disjoint");
}

// The cases, collected so `main` can catch exceptions and name the failing group.
void runEveryGroup() {
  executesRealGuestCode();
  reportsTypedExitOnBudgetExhaustion();
  refusesUnscopedAndStaleGenerations();
  originalCallReachesTheGuestBody();
  registersTheMeasuredHeapLeaf();
  everyClaimedResidentLeafIsBound();
  overlayReplacementRetiresThePriorGenerationsKeys();
}

} // namespace

int main() {
  try {
    runEveryGroup();
  } catch (const std::exception &error) {
    std::fprintf(stderr, "dynarec dispatch contract: an exception escaped a group: %s\n", error.what());
    return 1;
  } catch (...) {
    std::fprintf(stderr, "dynarec dispatch contract: a non-std exception escaped a group\n");
    return 1;
  }
  if (g_failures != 0) {
    std::fprintf(stderr, "dynarec dispatch contract: %d failure(s)\n", g_failures);
    return 1;
  }
  std::printf("dynarec dispatch contract: 8/8 groups passed\n");
  return 0;
}
