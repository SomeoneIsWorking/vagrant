#pragma once

class Core;

namespace vagrant {

// TITLE's guest libpress path owns STR streaming, VLC expansion, MDEC decode, double buffering, and
// RGB24 uploads into VRAM. This producer owns only the missing host scanout boundary: a completed
// guest frame makes the already-selected display buffer eligible for one native present at VBlank.
class TitleMovieProducer {
public:
  void frameCompleted();
  bool present(Core &core);

  bool frameReady() const {
    return frameReady_;
  }

private:
  bool frameReady_ = false;
};

void registerTitleMovieOverrides();
bool presentTitleMovie(Core &core);

} // namespace vagrant
