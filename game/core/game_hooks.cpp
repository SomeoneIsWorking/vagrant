// game_hooks.cpp — bounded compatibility callbacks not yet migrated into VagrantRuntime.
//
// There are exactly two kinds of member here, and the distinction is the point (the shape is taken
// from spider1/game/core/game_hooks.cpp, which learned it the hard way):
//
//   NEUTRAL   — the hook asks "what does the GAME's native code contribute here?", and the honest
//               answer while nothing is owned is "nothing". A neutral body is the CORRECT semantic,
//               not a placeholder.
//   FAIL-FAST — the hook is only reachable from a framework path this port has not stood up. Being
//               called means the run wandered into an un-RE'd path, and the only correct response is
//               to say so loudly and abort. A silent stub would let a half-wired path look like it
//               worked, which is the fake-green the porting doc warns about.
//
#include "cfg.h"
#include "core.h"
#include "game_iface.h"
#include "legacy_game_interface.h"
#include <stdlib.h>

// ── neutral ─────────────────────────────────────────────────────────────────────────────────────
static void vagrant_renderFadeState(Core *, FadeState *out) {
  out->mode = 0; // 0 == no fade; the present path leaves pixels untouched
  out->r = out->g = out->b = 0;
}

static void vagrant_renderBbFrameReset(Core *) {
  // No native billboard records are kept — nothing to reset.
}

static bool vagrant_hasNativeHandlerForEntry(Core *, uint32_t) {
  return false;
}
static int vagrant_devAreaCount(Core *) {
  return 0;
}
static const char *vagrant_devAreaName(Core *, int) {
  return "";
}
static bool vagrant_devWarpAllowed(Core *) {
  return false;
}

// ── fail-fast ───────────────────────────────────────────────────────────────────────────────────
static void unstood_up(const char *what) {
  cfg_loge("hooks",
           "%s was called, but this port has not stood that path up yet. Reaching it means "
           "the run entered an un-RE'd framework path — see docs/re-frontier.md. Refusing "
           "to continue with fabricated behaviour.",
           what);
  abort();
}

static void vagrant_frameUpdate(Core *) {
  unstood_up("frameUpdate (native frame loop)");
}
static void vagrant_drawOTag(Core *, uint32_t) {
  unstood_up("drawOTag (native frame loop)");
}
static int vagrant_schedStageBody(Core *, int, void *) {
  unstood_up("schedStageBody (PcScheduler)");
  return 0;
}
static bool vagrant_schedFreshEntry(Core *, int, uint32_t, uint32_t) {
  unstood_up("schedFreshEntry (PcScheduler)");
  return false;
}
static void vagrant_devWarp(Core *, int, int) {
  unstood_up("devWarp");
}

// DESIGNATED initialisers, deliberately — every hook binds BY NAME, so a field added upstream cannot
// slide this table by one (which, between two hooks of the same signature, compiles silently and calls
// the wrong function). C++20 requires designators in declaration order; keep them so when adding one.
// Unlisted members are value-initialised to null, so this list reads as the exact inventory of what
// this port has stood up.
static const GameHooks g_vagrant_hooks = {
    .frameUpdate = vagrant_frameUpdate,
    .drawOTag = vagrant_drawOTag,
    .schedFreshEntry = vagrant_schedFreshEntry,
    .hasNativeHandlerForEntry = vagrant_hasNativeHandlerForEntry,
    .renderFadeState = vagrant_renderFadeState,
    .renderBbFrameReset = vagrant_renderBbFrameReset,
    .devWarp = vagrant_devWarp,
    .devAreaCount = vagrant_devAreaCount,
    .devAreaName = vagrant_devAreaName,
    .devWarpAllowed = vagrant_devWarpAllowed,
    .schedStageBody = vagrant_schedStageBody,
};

const GameHooks &vagrant::legacy::compatibilityHooks = g_vagrant_hooks;
