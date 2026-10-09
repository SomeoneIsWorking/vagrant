#pragma once

#include <cstdint>

class Core;

namespace vagrant::cd {

struct LibDsFieldServices {
  using Call0 = std::uint32_t (*)(Core &, std::uint32_t);
  using Call2 = std::uint32_t (*)(Core &, std::uint32_t, std::uint32_t, std::uint32_t);

  Call0 call0 = nullptr;
  Call2 call2 = nullptr;
};

LibDsFieldServices productionLibDsFieldServices();

// Native owner of the libds transition formerly run from the guest VBlank callback.
class LibDsField {
public:
  LibDsField();
  explicit LibDsField(LibDsFieldServices services);

  void completeSynchronousInit(Core &core);
  void serviceField(Core &core);

  // libcd sent a controller command for libds; the next field delivers the completion its interrupt would.
  void commandSent() {
    completionOwed_ = true;
  }
  // Delivers the owed completion now. Retail runs it before the command's first sector; with instant reads the sector's
  // interrupt is ready first, so the sector hook calls this before it hands the sector over.
  void completeOwedCommand(Core &core);

  bool initialized() const {
    return initialized_;
  }

private:
  static void requireServices(const LibDsFieldServices &services);

  LibDsFieldServices services_;
  bool initialized_ = false;
  bool completionOwed_ = false;
};

} // namespace vagrant::cd
