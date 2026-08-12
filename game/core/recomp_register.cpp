// recomp_register.cpp — fills the framework↔generated-substrate seam (recomp_iface.h) from THIS
// game's recompiled symbols. This is the ONE file that names generated/ symbols; the framework
// reaches them only through psxport_recomp()->field.
//
// It therefore cannot compile until a substrate exists. `generated/` is produced by the recompiler,
// which needs this game's seed file and its overlay load bases — RE-02 and RE-03 in
// docs/re-frontier.md, neither done. The build reflects that honestly rather than papering over it:
// cmake/vagrant_port.cmake configures the port target ONLY when generated/rec_sources.cmake exists,
// and this file belongs to that target alone. The seam-check target (which DOES build today) compiles
// game_config.cpp / game_hooks.cpp / main.cpp against the framework headers and deliberately excludes
// this file.
//
// When the substrate lands, this becomes the shape spider1/game/core/recomp_register.cpp has: a
// designated-initialiser RecompRegistry naming main_dispatch, rec_func_index, the overlay table and
// shard_set_override from generated/overlay_table.h. It is left UNWRITTEN rather than written against
// guessed symbol names, because a plausible-looking wrong registry is exactly the kind of thing that
// reads as a framework bug later.
#include "core.h"
#include "recomp_iface.h"
#include "cfg.h"
#include <stdlib.h>

void vagrant_install_recomp() {
#ifdef VAGRANT_HAVE_SUBSTRATE
#error "A substrate now exists, so this file must be written for real: fill in the RecompRegistry \
from generated/overlay_table.h (see spider1/game/core/recomp_register.cpp) and delete this guard."
#else
  // No substrate: install nothing. NOT silent — a run that gets here has no recompiled code to
  // dispatch to, and finding that out at the first rec_dispatch would blame the wrong thing.
  cfg_loge("recomp", "no recompiled substrate is registered: generated/ has never been emitted for "
                     "this game (RE-02 seeds, RE-03 overlay bases — docs/re-frontier.md). Nothing can "
                     "execute. Refusing to continue.");
  abort();
#endif
}
