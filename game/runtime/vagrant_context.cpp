#include "runtime/vagrant_context.h"

#include "core.h"

#include <cstdlib>
#include <lucent/log.h>

namespace vagrant {

VagrantContext &contextOf(Core &core) {
  if (!core.gameCtx) {
    lucent::error("vagrant-core",
                  "a Vagrant Story owner reached a Core with no VagrantContext; the per-Core title "
                  "products were never created, so this is a composition defect rather than "
                  "guest-observable state");
    std::abort();
  }
  return *static_cast<VagrantContext *>(core.gameCtx);
}

} // namespace vagrant
