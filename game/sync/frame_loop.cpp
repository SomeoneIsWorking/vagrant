#include "sync/frame_loop.h"

#include "core.h"
#include "frame_pacer.h"
#include "game.h"
#include "render/battle_frame.h"
#include "render/title_menu.h"
#include "render/title_movie.h"
#include "render/title_startup.h"
#include "vagrant_context.h"

#include <cstdlib>
#include <lucent/log.h>

namespace {

vagrant::VagrantContext &context(Core &core) {
  if (!core.gameCtx) {
    lucent::error("vagrant-frame", "native frame reached without a VagrantContext");
    std::abort();
  }
  return *static_cast<vagrant::VagrantContext *>(core.gameCtx);
}

void serviceInput(Core &core) {
  context(core).padDelivery.serviceField(core);
}

void serviceAudio(Core &core) {
  core.game->spu_audio.frame();
}

void present(Core &core) {
  core.game->presentation.commit(&core);
}

void pace(Core &core) {
  gpu_pace_frame(&core);
}

void serviceLibDs(Core &core) {
  context(core).libDsField.serviceField(core);
}

void resumeFinitePhases(Core &core) {
  context(core).titleSplash.advanceAfterField(core);
  context(core).residentPhase.advanceAfterField(core);
}

} // namespace

namespace vagrant {

FrameServices productionFrameServices() {
  return {
      .input = serviceInput,
      .audio = serviceAudio,
      .titleStartup = prepareTitleStartupField,
      .titleMenu = prepareTitleMenuField,
      .battle = prepareBattleField,
      .titleMovie = prepareTitleMovieField,
      .present = present,
      .pace = pace,
      .libDs = serviceLibDs,
      .resumeResident = resumeFinitePhases,
  };
}

VagrantFrameDriver::VagrantFrameDriver() : VagrantFrameDriver(productionFrameServices()) {}

VagrantFrameDriver::VagrantFrameDriver(FrameServices services) : services_(services) {
  requireServices(services_);
}

void VagrantFrameDriver::requireServices(const FrameServices &services) {
  if (services.input && services.audio && services.titleStartup && services.titleMenu && services.battle &&
      services.titleMovie && services.present && services.pace && services.libDs && services.resumeResident) {
    return;
  }
  lucent::error("vagrant-frame", "VagrantFrameDriver requires every field service");
  std::abort();
}

void VagrantFrameDriver::stepFrame(Core &core, std::uint32_t frame) {
  // This is the host frame index used by host diagnostics and audio tagging. It deliberately does
  // not touch Sony's guest VBlank counter at 0x80032114; reaching guest VSync is fatal instead.
  core.game->timing.logicFrame = frame;
  core.game->timing.frameTick();
  core.rsub.otAttr.beginLogicFrame(frame);

  services_.input(core);
  services_.audio(core);

  // Preserve the previously measured field arbitration across the resident/TITLE/BATTLE outer
  // domains. A ready producer prepares its queue or guest-VRAM scanout; the single commit below is
  // the only presentation fence, including the resident fallback field.
  if (services_.titleStartup(core) || services_.titleMenu(core)) {
    lastFieldOwner_ = FieldOwner::Title;
  } else if (services_.battle(core)) {
    lastFieldOwner_ = FieldOwner::Battle;
  } else if (services_.titleMovie(core)) {
    lastFieldOwner_ = FieldOwner::Title;
  } else {
    lastFieldOwner_ = FieldOwner::Resident;
  }

  services_.present(core);
  services_.pace(core);

  // Pacing advances the title-owned display field and services the wall-locked CD controller. A
  // completed command raises the real CD IRQ and arms PW_IRQ; service that guest callback route at
  // this call-coherent native boundary. This is not a VBlank delivery and does not dispatch Sony
  // VSync: it is the hardware completion needed by the intact asynchronous libds queue.
  if ((core.pending_work & Core::PW_IRQ) != 0) {
    core.game->hle.irqPoll(&core);
  }
  services_.libDs(core);

  // A retail VSync resumes only after that field's input/audio/presentation work completes. Resume
  // the finite resident/TITLE tail at the same boundary; any GPU work it emits is committed on the
  // next field, and no guest routine gets to own or wait for iteration.
  services_.resumeResident(core);
}

} // namespace vagrant
