// Keeps `main` a single call so the product's order of operations reads in one place.
#include "boot/application.h"

int main(int argc, char **argv) {
  return vagrant::runApplication(argc, argv);
}
