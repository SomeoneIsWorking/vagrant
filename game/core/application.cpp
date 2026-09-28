#include "core/application.h"

#include "config.h"
#include "core.h"
#include "core/resident_image.h"
#include "core/dynarec_dispatch.h"
#include "core/native_owners.h"
#include "core/resident_image.h"
#include "core/vagrant_context.h"
#include "frame_loop_shell.h"
#include "game.h"
#include "hw_bind.h"
#include "lightrec_executor.h"
#include "memcensus.h"
#include "mods.h"
#include "platform_hle.h"
#include "render_capabilities.h"
#include "store_observe.h"
#include "sync/vsync_facts.h"
#include "vagrant_runtime.h"

#include <lucent/log.h>

#include <cstdlib>
#include <cstring>
#include <string>
#include <string_view>

extern "C" void watchdog_init();

namespace vagrant {
namespace {

// The one product executable path, relative to the repository root the launcher runs in. The
// launcher provisions it there; nothing here searches for media, because provisioning is a launcher
// concern and a second discovery order would be a second answer to "which bytes".
constexpr std::string_view kResidentImagePath = "scratch/bin/vagrant/SLUS_010.40";

// The measured Sony libetc VSync body, and nothing else, admitted into PlatformHle. psxport binds
// its mandatory native-frame-loop fatal handler there, so a retail busy-wait cannot run and report a
// misleading timeout. The window is exactly one instruction wide on purpose: no other resident
// library function has been classified as a native hardware-service boundary in this title.
PlatformHlePlan measuredPlatformPlan() {
  PlatformHlePlan plan{};
  plan.vsyncAddress = sync::kVSync;
  plan.windowLo[0] = sync::kVSync;
  plan.windowHi[0] = sync::kVSyncWindowEnd;
  return plan;
}

} // namespace

Application::Application() = default;

bool Application::start(Game &game, const std::string &residentImagePath) {
  if (started_) {
    lucent::error("vagrant-boot", "the Vagrant Story product was started more than once on one machine");
    return false;
  }
  Core &core = game.core;
  if (core.gameCtx == nullptr) {
    lucent::error("vagrant-boot",
                  "Game construction did not create this Core's VagrantContext, so the title's "
                  "per-Core products are absent; refusing before any guest state is touched");
    return false;
  }
  auto &context = contextOf(core);

  const auto image = readResidentImage(residentImagePath);
  if (!image) {
    return false;
  }
  auto &runtime = dynamic_cast<VagrantRuntime &>(*core.runtime);
  const auto published = runtime.loadResidentImage(core, image->bytes, kResidentImageName);
  if (!published) {
    lucent::error("vagrant-boot",
                  "the measured SLUS_010.40 header was refused for '{}': {}",
                  residentImagePath,
                  published.detail);
    return false;
  }
  psx::cpu::applyPsxExeTopLevelRegisters(core, published.image);
  residentImage_ = published.identity.value();
  started_ = true;

  lucent::info("vagrant-boot",
               "authenticated resident image: {} ({} bytes, sha256 {}), entry 0x{:08X}, text "
               "0x{:08X}+0x{:X}, stack 0x{:08X}, image {}/{}",
               residentImagePath,
               image->declaredSize,
               image->sha256,
               published.image.entry,
               published.image.textAddress,
               published.image.textBytes,
               published.image.stackBase,
               residentImage_.id,
               residentImage_.generation);

  // The per-Core hardware binds, in the framework's measured order. These are per-instance, so two
  // Cores keep separate peripheral state; doing them here rather than inside the title adapter is
  // what keeps the adapter about title behavior.
  gte_init();
  gte_bind(&core);
  core.rsub.projprim.bind(&core);
  spu_bind(&core);
  mdec_bind(&core);
  xa_bind(&core);
  game.spu_audio.init();
  game.gpu.gpu_native_init();
  game.pad.overridesInit();
  game.disc.env_key = "PSXPORT_VAGRANT_DISC";

  const auto registration = installResidentNativeOwners(core, residentImage_);
  if (!registration) {
    lucent::error("vagrant-boot",
                  "the resident generation published but its native leaves were not fully registered; "
                  "a partially owned image is a wrong measurement rather than a missing one, so the "
                  "product does not start");
    return false;
  }

  // The framework's platform sync preflight. This is where a title with no measured VSync address is
  // refused, and it must happen BEFORE boot, so a product without a host frame boundary cannot enter
  // guest main at all.
  FrameLoopShell{}.prepareProduct(game);
  lucent::info("vagrant-boot",
               "guest VSync 0x{:08X} is the measured fatal host boundary; the title frame driver owns "
               "iteration and no guest routine waits on a field",
               sync::kVSync);
  return true;
}

void Application::run(Game &game) {
  Core &core = game.core;
  FrameLoopShell shell;
  if (!started_) {
    lucent::error("vagrant-boot", "the Vagrant Story product loop was entered before the resident image was published");
    std::abort();
  }

  // The measured boot phase. `ResidentPhase` owns the finite resident leaf order and turns each
  // measured guest field wait into an explicit host state; the title's own `bootInit` is where that
  // is invoked, so the entry here stays the composition boundary.
  core.runtime->bootInit(core);

  psx::config::report_once();
  lucent::info("vagrant-boot", "entering the bounded Vagrant Story product loop");
  // The live control channel is started here rather than in the adapter, beside the loop it serves,
  // because a surface nobody opens is not a surface.
  core.game->dbg_server.start(&core);
  store_observe_configure(core);
  for (std::uint32_t frame = 0;; ++frame) {
    core.game->dbg_server.honourPause(&core);
    shell.step(core, frame);
    core.game->dbg_server.service(&core);
  }
}

void Application::reportRunEnd(Game &game) const {
  const auto &execution = game.core.lightrecExecutor().counters();
  const auto &context = contextOf(game.core);

  // The framework-owned half. `translatedBlocks` and `executedBlocks` are the dynarec evidence; a run
  // that translated blocks and interpreted none is the claim S015 rests on. `fallback.calls` is the
  // number that must be ZERO for a dynarec-only product, and it is reported with its own per-reason
  // breakdown so a zero cannot be read as "nobody counted".
  game.core.lightrecExecutor().reportFallbackTelemetry("vagrant run-end");
  lucent::info("vagrant-boot",
               "Lightrec run-end: {} dispatch call(s), {} translated block(s), {} executed block(s), {} "
               "executed instruction(s), {} cache hit(s) of {} lookup(s), {} invalidation(s), {} fault(s)",
               execution.calls,
               execution.translatedBlocks,
               execution.executedBlocks,
               execution.executedInstructions,
               execution.cacheHits,
               execution.cacheHits + execution.cacheMisses,
               execution.invalidations,
               execution.faults);

  // The title-owned half, every counter with its denominator.
  context.executionTelemetry.report("vagrant-boot");
  lucent::info("vagrant-boot",
               "the guest-leg producer census recorded {} OT span(s) with {} overflow(s); a zero here "
               "means the guest submitted no primitive in this run, which is a fact about the frame "
               "and not about the instrument",
               game.core.rsub.otAttr.spanCount(),
               game.core.rsub.otAttr.spanOverflow());
  // The call-site byte census, when it was armed. Its own report names the blind spots it cannot
  // see, so calling dump() unconditionally is correct and not a second policy: it is a no-op
  // without the knob.
  memcensus_dump();
}

int runApplication(int argc, char **argv) {
  for (int index = 1; index < argc; ++index) {
    if (std::strcmp(argv[index], "-h") == 0 || std::strcmp(argv[index], "--help") == 0) {
      lucent::info("vagrant-boot", "Usage: {} [--resident PATH]", argv[0]);
      lucent::info("vagrant-boot",
                   "Run Vagrant Story (USA SLUS_010.40) through psxport's Lightrec dynarec executor. "
                   "The default resident path is {}; the launcher provisions it.",
                   kResidentImagePath);
      return EXIT_SUCCESS;
    }
  }
  std::string residentImage{ kResidentImagePath };
  for (int index = 1; index < argc; ++index) {
    if (std::strcmp(argv[index], "--resident") == 0 && index + 1 < argc) {
      residentImage = argv[++index];
      continue;
    }
    lucent::error("vagrant-boot", "unrecognised argument '{}'; run with --help", argv[index]);
    return 2;
  }

  auto game = std::make_unique<Game>();
  if (!game->core.lightrecExecutor().available()) {
    lucent::error("vagrant-boot",
                  "psxport was built without its Lightrec dynarec backend. There is no interpreter "
                  "fallback and no engine selector: the product is unavailable, not degraded");
    return 2;
  }
  watchdog_init();

  Application application;
  if (!application.start(*game, residentImage)) {
    return 2;
  }
  application.run(*game);
  application.reportRunEnd(*game);
  return EXIT_SUCCESS;
}

} // namespace vagrant
