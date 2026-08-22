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
    // The generated table currently owns the SHA-verified TITLE module. Every other measured overlay
    // remains absent and therefore fails fast if reached; the router never substitutes TITLE merely
    // because another image occupies the same fixed slot.
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
