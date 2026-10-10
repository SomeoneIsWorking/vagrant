#include "boot/application.h"

#include "boot/resident_image.h"
#include "c_subsys.h"
#include "config.h"
#include "core.h"
#include "execution/dynarec_dispatch.h"
#include "frame_loop_shell.h"
#include "game.h"
#include "hw_bind.h"
#include "lightrec_executor.h"
#include "machine.h"
#include "memcensus.h"
#include "mods.h"
#include "platform_hle.h"
#include "render_capabilities.h"
#include "runtime/vagrant_context.h"
#include "runtime/vagrant_runtime.h"
#include "store_observe.h"
#include "sync/vsync_facts.h"

#include <lucent/log.h>

#include <cstdlib>
#include <cstring>
#include <string>
#include <string_view>

namespace vagrant {
namespace {

// Relative to the repository root; the launcher provisions it.
constexpr std::string_view kResidentImagePath = "scratch/bin/vagrant/SLUS_010.40";

// Namespace-scope so it outlives the Core that snapshots it, not a runApplication local.
VagrantRuntime titleRuntime;

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
  // The load is refused if any image-scoped native leaf is refused.
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
  // Every image-scoped leaf is registered and looked up against this generation.
  residentImage_ = published.identity.value_or(psx::cpu::ImageIdentity{});
  if (residentImage_ == psx::cpu::ImageIdentity{}) {
    lucent::error("vagrant-boot",
                  "the authenticated resident image published no generation identity, so no "
                  "image-scoped native leaf can be registered against it; refusing to start");
    return false;
  }
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

  // Per-Core hardware binds, in the framework's order.
  gte_init();
  gte_bind(&core);
  core.rsub.projprim.bind(&core);
  spu_bind(&core);
  mdec_bind(&core);
  xa_bind(&core);
  game.spu_audio.init();
  game.gpu.gpu_native_init();
  game.pad.overridesInit();
  game.disc.env_key = runtime.discEnvVar();

  // Refuses a title with no measured VSync address; must precede boot.
  psx::frame::FrameLoopShell{}.prepareProduct(game);
  lucent::info("vagrant-boot",
               "guest VSync 0x{:08X} is the measured fatal host boundary; the title frame driver owns "
               "iteration and no guest routine waits on a field",
               sync::kVSync);
  return true;
}

void Application::run(Game &game) {
  Core &core = game.core;
  if (!started_) {
    lucent::error("vagrant-boot", "the Vagrant Story product loop was entered before the resident image was published");
    std::abort();
  }

  psx::Machine machine{game};
  machine.installRenderPath();
  core.runtime->bootInit(core);

  psx::config::report_once();
  lucent::info("vagrant-boot", "entering the bounded Vagrant Story product loop");

  machine.attachControlChannel(0u);
  machine.run(0u);
}

void Application::reportRunEnd(Game &game) const {
  const auto &execution = game.core.lightrecExecutor().counters();

  // `fallback.calls` must be zero for a dynarec-only product.
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

  lucent::info("vagrant-boot",
               "the guest-leg producer census recorded {} OT span(s) with {} overflow(s); a zero here "
               "means the guest submitted no primitive in this run, which is a fact about the frame "
               "and not about the instrument",
               game.core.rsub.otAttr.spanCount(),
               game.core.rsub.otAttr.spanOverflow());
  // No-op unless the call-site byte census was armed.
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
  std::string residentImage{kResidentImagePath};
  for (int index = 1; index < argc; ++index) {
    if (std::strcmp(argv[index], "--resident") == 0 && index + 1 < argc) {
      residentImage = argv[++index];
      continue;
    }
    lucent::error("vagrant-boot", "unrecognised argument '{}'; run with --help", argv[index]);
    return 2;
  }

  // Core::Core() reads this once, at construction.
  psxport_install_game(titleRuntime);

  auto game = std::make_unique<Game>();
  if (game->core.runtime == nullptr || game->core.gameCtx == nullptr) {
    lucent::error("vagrant-boot",
                  "the installed GameRuntime produced no per-Core context, so no title product exists "
                  "for this Core; refusing before any guest state is touched");
    return 2;
  }
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
