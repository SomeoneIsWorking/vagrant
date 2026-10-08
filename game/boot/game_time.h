#pragma once

class Core;

namespace vagrant::game_time {

// Non-VSync part of resident `vs_main_gametimeUpdate` 0x8004261C.
void advance(Core &core);

} // namespace vagrant::game_time
