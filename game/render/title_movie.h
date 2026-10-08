#pragma once

class Core;

namespace vagrant {

// TITLE's guest libpress path decodes and uploads frames; this producer only exposes the display buffer scanout.
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
