#pragma once

#include "game_runtime.h"

#include <cstdint>

class Core;

namespace vagrant {

// The outer domains with presentation fences; host metadata only.
enum class FieldOwner {
  Resident,
  Title,
  Battle,
};

// Dependency seam so tests drive the production VagrantFrameDriver body.
struct FrameServices {
  using FieldService = void (*)(Core &);
  using ProducerService = bool (*)(Core &);

  FieldService input = nullptr;
  FieldService audio = nullptr;
  ProducerService titleStartup = nullptr;
  ProducerService titleMenu = nullptr;
  ProducerService battle = nullptr;
  ProducerService titleMovie = nullptr;
  FieldService present = nullptr;
  FieldService pace = nullptr;
  FieldService libDs = nullptr;
  FieldService resumeResident = nullptr;
};

FrameServices productionFrameServices();

// One display field; the title-owned driver owns the field order and exactly one presentation fence.
class VagrantFrameDriver final : public FrameDriver {
public:
  VagrantFrameDriver();
  explicit VagrantFrameDriver(FrameServices services);

  void stepFrame(Core &core, std::uint32_t frame) override;

  FieldOwner lastFieldOwner() const {
    return lastFieldOwner_;
  }

private:
  static void requireServices(const FrameServices &services);

  FrameServices services_;
  FieldOwner lastFieldOwner_ = FieldOwner::Resident;
};

} // namespace vagrant
