# Vagrant Story (SLUS-01040, USA) — a PC-native port built on the psxport framework
# (external/psxport submodule).
#
# The framework (PSX-generic static-recomp substrate + runtime + HW backends + SBS harness + SDL_GPU
# renderer) is the reusable `psxport` library; this repo adds the game (game/**) and the gitignored,
# reproducibly emitted SLUS_010.40 substrate (generated/**). See docs/re-frontier.md for the current
# verified boundary.
cmake_minimum_required(VERSION 3.21)

# ccache, when available. The recompiled substrate is hundreds of MB of generated C, so compilation is
# essentially the whole cost of an iteration. Must be set BEFORE project(), which is when CMake probes
# the compiler.
find_program(CCACHE_PROGRAM ccache)
if(CCACHE_PROGRAM)
  set(CMAKE_C_COMPILER_LAUNCHER   "${CCACHE_PROGRAM}")
  set(CMAKE_CXX_COMPILER_LAUNCHER "${CCACHE_PROGRAM}")
  message(STATUS "ccache: ${CCACHE_PROGRAM}")
endif()

project(vagrantstory CXX C)

# PSXPORT_DIR — WHERE THE FRAMEWORK SOURCE COMES FROM. Defaults to the pinned submodule, so a fresh
# clone of this repo alone builds standalone: that property is what "each game is its own project using
# psxport as the framework" means, and it must stay testable.
#
# Point it at the workspace's framework DEV CLONE to build against in-progress framework work WITHOUT
# editing the submodule (the submodule is a READ-ONLY pinned consumer; framework edits happen in one
# place only — external/psxport/docs/workspace/PROTOCOL.md):
#
#   cmake -S . -B build -DPSXPORT_DIR=/path/to/psxport
#
# It is a CACHE path, so it survives reconfigures. Everything else in this file and in cmake/ derives
# from it — never re-spell `external/psxport` at a call site, or the two halves of a build can come
# from different checkouts.
set(PSXPORT_DIR "${CMAKE_SOURCE_DIR}/external/psxport" CACHE PATH
    "psxport framework source directory (default: the external/psxport submodule)")
if(NOT EXISTS "${PSXPORT_DIR}/cmake/psxport.cmake")
  message(FATAL_ERROR "PSXPORT_DIR=${PSXPORT_DIR} has no cmake/psxport.cmake — "
                      "run `git submodule update --init external/psxport`, or point PSXPORT_DIR at a psxport checkout.")
endif()
message(STATUS "psxport framework: ${PSXPORT_DIR}")

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

find_package(ZLIB REQUIRED)
find_package(zstd CONFIG QUIET)
if(NOT TARGET zstd::libzstd_shared)
  find_library(ZSTD_LIBRARY zstd REQUIRED)
  add_library(zstd::libzstd_shared SHARED IMPORTED)
  set_target_properties(zstd::libzstd_shared PROPERTIES IMPORTED_LOCATION "${ZSTD_LIBRARY}")
endif()
find_package(Threads REQUIRED)

# libchdr (CHD access) comes from the Beetle PSX submodule NESTED under psxport (PSXPORT_DIR, above).
add_subdirectory(${PSXPORT_DIR}/vendor/beetle-psx/deps/libchdr
                 ${CMAKE_BINARY_DIR}/libchdr_build EXCLUDE_FROM_ALL)

include(cmake/vagrant_port.cmake)
