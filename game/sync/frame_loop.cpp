#include "sync/frame_loop.h"

#include "core.h"
#include "frame_pacer.h"
#include "game.h"
#include "render/battle_frame.h"
#include "render/title_menu.h"
#include "render/title_movie.h"
#include "render/title_startup.h"
#include "runtime/vagrant_context.h"

#include <cstdlib>
#include <lucent/log.h>

namespace {

void serviceInput(Core &core) {
  vagrant::contextOf(core).padDelivery.serviceField(core);
}

void serviceAudio(Core &core) {
  core.game->spu_audio.frame();
}

void present(Core &core) {
  core.game->presentation.commit(&core);
}

void pace(Core &core) {
  core.game->framePacer.paceFrame(core);
}

void serviceLibDs(Core &core) {
  vagrant::contextOf(core).libDsField.serviceField(core);
}

void resumeFinitePhases(Core &core) {
  vagrant::contextOf(core).titleSplash.advanceAfterField(core);
  vagrant::contextOf(core).residentPhase.advanceAfterField(core);
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

VagrantFrameDriver::VagrantFrameDriver() : VagrantFrameDriver(productionFrameServices()) {
}

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
  // Host frame index for diagnostics and audio; never touches the guest VBlank counter at 0x80032114.
  core.game->timing.logicFrame = frame;
  core.game->timing.frameTick();
  core.rsub.otAttr.beginLogicFrame(frame);

  services_.input(core);
  services_.audio(core);

  // A ready producer prepares its queue or VRAM scanout; the single commit below is the presentation fence.
  if (services_.titleStartup(core) || services_.titleMenu(core)) {
    lastFieldOwner_ = FieldOwner::Title;
  } else if (services_.battle(core)) {
    lastFieldOwner_ = FieldOwner::Battle;
  } else {
    lastFieldOwner_ = services_.titleMovie(core) ? FieldOwner::Title : FieldOwner::Resident;
  }

  services_.present(core);
  services_.pace(core);

  // Service the CD IRQ guest callback at this boundary; not a VBlank delivery.
  if ((core.pending_work & Core::PW_IRQ) != 0) {
    core.game->hle.irqPoll(&core);
  }
  services_.libDs(core);

  // Resume the resident/TITLE tail after the field; its GPU work commits on the next field.
  services_.resumeResident(core);
}

} // namespace vagrant
