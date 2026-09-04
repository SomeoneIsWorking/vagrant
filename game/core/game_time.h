#pragma once

class Core;

namespace vagrant::game_time {

// Non-VSync state transition from resident vs_main_gametimeUpdate 0x8004261C. Field ownership is
// supplied by VagrantFrameDriver; this function preserves the retail packed time update exactly.
void advance(Core &core);

} // namespace vagrant::game_time
