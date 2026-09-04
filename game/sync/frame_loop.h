#pragma once

#include "game_runtime.h"

#include <cstdint>

class Core;

namespace vagrant {

// The three retail outer domains whose completed presentation fences are currently measured. This
// is host ownership metadata only; it is not written into guest RAM and does not impersonate Sony's
// retired VBlank counter.
enum class FieldOwner {
  Resident,
  Title,
  Battle,
};

// Narrow dependency seam for the one shipping frame operation. Tests substitute these operations
// to prove ordering and short-circuit ownership through the production VagrantFrameDriver body.
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

// One finite Vagrant Story display field. The framework shell owns iteration; this title-owned
// driver owns the measured field order and exactly one presentation fence.
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
