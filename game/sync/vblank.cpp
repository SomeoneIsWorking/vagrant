// Vagrant Story's resident VBlank delivery seam.
//
// The console installs 0x8001FFEC as its VBlank interrupt handler from startIntrVSync. That guest
// handler owns the semantics of a display field: it increments libetc's counter at 0x80032114 and
// dispatches all eight callbacks registered in the table at 0x800320F4. The host owns only WHEN a
// real display field occurs. Dispatching the intact guest handler keeps the counter, libpad, and any
// later callback users on their original path instead of replacing one observed counter with a host
// tick.
#include "vblank.h"

#include "core.h"
#include "game.h"
#include "override_registry.h"
#include "render/battle_frame.h"
#include "render/title_menu.h"
#include "render/title_movie.h"
#include "render/title_startup.h"
#include "vagrant_context.h"
#include <lucent/log.h>

extern void gen_func_8001FF94(Core *);
extern void shard_set_override(uint32_t, void (*)(Core *));

namespace {

// RE-10: tools/re_vblank.py derives both entries from the SHA-verified executable and gates their
// uses below. startIntrVSync is the arming boundary; registering earlier would deliver an interrupt
// before the guest installed its handler and cleared its callback table.
constexpr uint32_t kStartIntrVSync = 0x8001FF94u;
constexpr uint32_t kVBlankHandler = 0x8001FFECu;
constexpr uint32_t kVBlankCounter = 0x80032114u;

bool s_clockArmed = false;

void vagrant_vblank_turn(Core *c) {
  const uint32_t before = c->mem_r32(kVBlankCounter);
  rec_dispatch(c, kVBlankHandler);
  // RE-06 measured the two buffers consumed by Vagrant Story's intact libpad state decoder. The
  // resident program never returns to psxport's generic native frame loop, so this owned display
  // field is also the only faithful point at which host input can replace the console's VBlank SIO
  // transfer before guest code resumes and reads those buffers.
  static_cast<vagrant::VagrantContext *>(c->gameCtx)->padDelivery.serviceField(*c);
  // The resident program likewise never reaches a framework per-field tick, so the SPU mixer has
  // exactly one driver: this display field. Advancing it here is what makes CD-XA pulls happen
  // (CDC_GetCDAudioSample lives inside spu_update) — without it the XA ring fills and drops while
  // rd never moves, and every SPU-produced sound (movie audio, BGM, voices) stays silent.
  c->game->spu_audio.frame();
  // The two TITLE products occupy consecutive guest phases. Keep one present per field even at the
  // transition: an immediate splash sprite wins the field; otherwise a completed MDEC frame scans out.
  // BATTLE has its own retail-measured completed-presenter fence. The final commit remains an honest
  // fallback for overlays whose frame owner has not yet been measured; it is not BATTLE's owner.
  if (!vagrant::presentTitleStartup(*c) && !vagrant::presentTitleMenu(*c)) {
    if (!vagrant::presentBattleFrame(*c) && !vagrant::presentTitleMovie(*c)) {
      c->game->presentation.commit(c);
    }
  }
  lucent::debug("vagrant-vblank", "guest VBlank handler advanced counter {} -> {}", before, c->mem_r32(kVBlankCounter));
}

void vagrant_start_intr_vsync(Core *c) {
  // Super-call first: the guest clears its callback table/counter, installs the interrupt handler,
  // and returns its VSyncCallback registrar. ResetCallback's caller consumes that return value.
  gen_func_8001FF94(c);
  if (s_clockArmed) {
    return;
  }

  // One field-rate authority: the framework decodes the video standard the game selected. There is
  // deliberately no 60 Hz literal and no host-side counter increment here.
  rec_host_turn_register(c, vagrant_vblank_turn, gpu_field_rate_millihz(c));
  s_clockArmed = true;
  lucent::info("vagrant-vblank", "resident VBlank delivery armed after guest startIntrVSync");
}

} // namespace

void vagrant_vblank_register_overrides() {
  overrides::install(kStartIntrVSync,
                     "VagrantVBlank::startIntrVSync",
                     vagrant_start_intr_vsync,
                     gen_func_8001FF94,
                     shard_set_override);
}
