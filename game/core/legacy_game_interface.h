#pragma once

struct GameConfig;
struct GameHooks;

namespace vagrant::legacy {

// These tables are compatibility debt for generic framework algorithms that still read
// Core::cfg/Core::hooks. VagrantRuntime is the title's public ownership seam; new behavior belongs
// on that derived runtime, and new measured facts belong in narrow typed interfaces.
extern const GameConfig &measuredConfig;
extern const GameHooks &compatibilityHooks;

} // namespace vagrant::legacy
