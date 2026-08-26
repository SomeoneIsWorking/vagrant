#pragma once

class Core;

namespace vagrant {

class BattleFrameProducer {
public:
  void frameCompleted();
  bool present(Core &core);

  bool frameReady() const {
    return frameReady_;
  }

private:
  bool frameReady_ = false;
};

void registerBattleFrameOverrides();
bool presentBattleFrame(Core &core);

} // namespace vagrant
