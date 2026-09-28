// The process entry point. It owns nothing: `vagrant::runApplication` is the composition owner, and
// this translation unit exists so the shipped executable has a `main` that is a single call, which
// is what makes the product's order of operations readable in one place.
#include "core/application.h"

int main(int argc, char **argv) {
  return vagrant::runApplication(argc, argv);
}
