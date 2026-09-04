#pragma once

#include <cstdint>

class Core;

namespace vagrant::cd {

struct LibDsFieldServices {
  using Call0 = void (*)(Core &, std::uint32_t);

  Call0 call0 = nullptr;
};

LibDsFieldServices productionLibDsFieldServices();

// Native-field owner for the finite libds state transition formerly reached from the guest's VBlank
// callback. Low-level CD-init commands are synchronous under psxport, so their measured libds Ready
// postcondition is established explicitly before field service begins.
class LibDsField {
public:
  LibDsField();
  explicit LibDsField(LibDsFieldServices services);

  void completeSynchronousInit(Core &core);
  void serviceField(Core &core);

  bool initialized() const {
    return initialized_;
  }

private:
  static void requireServices(const LibDsFieldServices &services);

  LibDsFieldServices services_;
  bool initialized_ = false;
};

} // namespace vagrant::cd
