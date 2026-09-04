#pragma once

class Core;

namespace vagrant {

// TITLE's guest libpress path owns STR streaming, VLC expansion, MDEC decode, double buffering, and
// RGB24 uploads into VRAM. This producer owns only the missing host scanout boundary: a completed
// guest frame makes the already-selected display buffer eligible for the native driver's next field.
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

bool prepareTitleMovieField(Core &core);

} // namespace vagrant
