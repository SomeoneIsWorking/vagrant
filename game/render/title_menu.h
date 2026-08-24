#pragma once

class Core;

namespace vagrant {

class TitleMenuProducer {
public:
  void frameCompleted();
  bool present(Core &core);

  bool frameReady() const {
    return frameReady_;
  }

private:
  bool frameReady_ = false;
};

void registerTitleMenuOverrides();
bool presentTitleMenu(Core &core);

} // namespace vagrant
