// recomp_register.cpp — fills psxport's framework↔generated-substrate seam from this game's generated
// symbols. The framework remains independent of generated code; this is the sole adapter.
#include "core.h"
#include "overlay_table.h"
#include "recomp_iface.h"

// Generated in shard_disp.c with this exact signature.
extern void shard_set_override(uint32_t, void (*)(Core *));

static const RecompRegistry g_vagrant_recomp = {
    /* main_dispatch        */ main_dispatch,
    /* rec_func_index       */ rec_func_index,
    // The first substrate is deliberately resident-only. Runtime-reached overlay calls therefore
    // fail fast instead of executing an unverified module. Overlay emission is the next growth step.
    /* overlays             */ g_rec_overlays,
    /* overlay_count        */ g_rec_overlay_count,
    /* shard_set_override   */ shard_set_override,
    /* ov_a00_set_override  */ nullptr,
    /* ov_game_set_override */ nullptr,
    // No Vagrant Story memset fast-path has been identified; the recompiled guest body remains live.
    /* guestMemset_gen      */ nullptr,
};

void vagrant_install_recomp() {
  psxport_install_recomp(&g_vagrant_recomp);
}
