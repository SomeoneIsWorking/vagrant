# cmake/vagrant_port.cmake — framework, seam, and generated-substrate targets.
#
# Three targets:
#
#   psxport            the framework static library (+ psxport_smoke, its agnosticism proof). Always
#                      configured, so `cmake --build build --target psxport_smoke` works from a bare
#                      clone of this repo with nothing game-specific present.
#   vagrant_seam       AN OBJECT LIBRARY over the shared game TUs (derived runtime / bounded legacy
#                      facts / main / CD and VBlank owners).
#                      It COMPILES but does not link, which is exactly the check possible before a
#                      substrate exists: it proves VagrantRuntime and its bounded legacy facts still
#                      satisfy the pinned framework seam — every designator and virtual binds.
#                      That is the gate for this repo today (`--target vagrant_seam`).
#   vagrant_port       the game binary. Configured when the gitignored generated resident + TITLE
#                      substrate exists.

option(PSXPORT_BUILD_PORT "Build the Vagrant Story native port binary (needs generated/)" ON)

# The framework static library + its psxport_smoke agnosticism proof. Always included so `psxport` is
# buildable even when the game target is off.
include(${PSXPORT_DIR}/cmake/psxport.cmake)

# ---- the seam, compile-only --------------------------------------------------------------------
# recomp_register.cpp is excluded because it is the one TU that names generated symbols.
set(GAME_SRC
  game/core/game_config.cpp
  game/core/game_heap.cpp
  game/core/game_hooks.cpp
  game/core/main.cpp
  game/core/vagrant_runtime.cpp
  game/input/pad_delivery.cpp
  game/render/battle_frame.cpp
  game/render/title_menu.cpp
  game/render/title_movie.cpp
  game/render/title_startup.cpp
  game/render/title_startup_recipe.cpp
  game/cd/ds_control.cpp
  game/sync/vblank.cpp
)
add_library(vagrant_seam OBJECT ${GAME_SRC})
set_target_properties(vagrant_seam PROPERTIES CXX_STANDARD 17 CXX_STANDARD_REQUIRED ON)
target_include_directories(vagrant_seam PRIVATE game game/core)
# Links only for its INTERFACE include directories — an OBJECT library performs no link step, which is
# the whole point: no substrate is needed to check that the seam is well-formed.
target_link_libraries(vagrant_seam PRIVATE psxport)
target_compile_options(vagrant_seam PRIVATE -g)

# This test compiles the exact command classifier used by the shipping owner. It needs neither the
# provisioned executable nor generated code, so a bare clone can prove every accepted control ID and
# the refusal side of the ownership boundary.
if(BUILD_TESTING)
  include(CTest)

  add_executable(vagrant_cd_contract_test tests/test_ds_control_contract.cpp)
  set_target_properties(vagrant_cd_contract_test PROPERTIES
    CXX_STANDARD 17 CXX_STANDARD_REQUIRED ON)
  target_include_directories(vagrant_cd_contract_test PRIVATE game)
  add_test(NAME vagrant_cd_contract_test COMMAND vagrant_cd_contract_test)
  add_test(
    NAME vagrant_launcher_test
    COMMAND ${Python3_EXECUTABLE} ${CMAKE_SOURCE_DIR}/tests/test_launcher.py)
  add_test(
    NAME vagrant_overlay_inputs_test
    COMMAND ${Python3_EXECUTABLE} ${CMAKE_SOURCE_DIR}/tests/test_overlay_inputs.py)
  add_test(
    NAME vagrant_cpp_quality
    COMMAND ${Python3_EXECUTABLE} ${PSXPORT_DIR}/tools/check_cpp_style.py
            --root ${CMAKE_SOURCE_DIR} --compile-commands ${CMAKE_BINARY_DIR})
  add_executable(vagrant_runtime_test
    tests/test_vagrant_runtime.cpp
    game/core/game_config.cpp
    game/core/game_heap.cpp
    game/core/game_hooks.cpp
    game/core/vagrant_runtime.cpp
    game/input/pad_delivery.cpp
    game/render/battle_frame.cpp
    game/render/title_menu.cpp
    game/render/title_movie.cpp
    game/render/title_startup.cpp
    game/render/title_startup_recipe.cpp)
  target_include_directories(vagrant_runtime_test PRIVATE game game/core)
  target_link_libraries(vagrant_runtime_test PRIVATE psxport)
  set_target_properties(vagrant_runtime_test PROPERTIES
    CXX_STANDARD 20 CXX_STANDARD_REQUIRED ON)
  add_test(NAME vagrant_runtime_test COMMAND vagrant_runtime_test)
  add_executable(vagrant_game_heap_test
    tests/test_game_heap.cpp
    game/core/game_heap.cpp)
  target_include_directories(vagrant_game_heap_test PRIVATE game game/core)
  target_link_libraries(vagrant_game_heap_test PRIVATE psxport)
  set_target_properties(vagrant_game_heap_test PROPERTIES
    CXX_STANDARD 20 CXX_STANDARD_REQUIRED ON)
  add_test(NAME vagrant_game_heap_test COMMAND vagrant_game_heap_test)
  add_executable(vagrant_title_recipe_test
    tests/test_title_startup_recipe.cpp
    game/render/title_startup_recipe.cpp)
  target_include_directories(vagrant_title_recipe_test PRIVATE game/render)
  set_target_properties(vagrant_title_recipe_test PROPERTIES
    CXX_STANDARD 20 CXX_STANDARD_REQUIRED ON)
  add_test(NAME vagrant_title_recipe_test COMMAND vagrant_title_recipe_test)
endif()

if(NOT PSXPORT_BUILD_PORT)
  return()
endif()

if(NOT EXISTS ${CMAKE_SOURCE_DIR}/generated/rec_sources.cmake)
  message(STATUS
    "vagrant_port: NOT configured — generated/rec_sources.cmake is absent, i.e. the recompiled "
    "substrate has not been emitted in this checkout. Run the documented RE-02 emit command; "
    "`--target vagrant_seam` remains available without generated code.")
  return()
endif()

# ---- the recompiled substrate --------------------------------------------------------------------
# emit.py writes the exact TU list to generated/rec_sources.cmake (GEN_REC_SRCS, basenames), so the set
# is deterministic — no globbing, which would wrongly pull unlinked stub TUs.
#
# -foptimize-sibling-calls IS REQUIRED, NOT an optimisation nicety: a guest TAIL JUMP is emitted as
# `dispatch(c,x); return;` in tail position and the guest uses such tail jumps for loops that iterate
# indefinitely. Without sibling-call optimisation each iteration becomes a real C call, the stack grows
# per loop, and the process SIGSEGVs.
include(${CMAKE_SOURCE_DIR}/generated/rec_sources.cmake)
list(TRANSFORM GEN_REC_SRCS PREPEND generated/)
set_source_files_properties(${GEN_REC_SRCS}
  PROPERTIES LANGUAGE CXX
  COMPILE_OPTIONS "-O1;-foptimize-sibling-calls;-fno-strict-aliasing;-fwrapv")

add_executable(vagrant_port ${GAME_SRC} game/core/recomp_register.cpp ${GEN_REC_SRCS})

target_compile_definitions(vagrant_port PRIVATE VAGRANT_HAVE_SUBSTRATE=1)

# The framework's SDL_GPU shader header is produced by a psxport custom target; gpu_vk.cpp (inside
# libpsxport) needs it present before this target's link ordering.
add_dependencies(vagrant_port gen_gpu_shaders)

set_target_properties(vagrant_port PROPERTIES
  CXX_STANDARD 17 CXX_STANDARD_REQUIRED ON
  ENABLE_EXPORTS ON                                    # -rdynamic: watchdog backtrace symbol names
  RUNTIME_OUTPUT_DIRECTORY ${CMAKE_SOURCE_DIR}/scratch/bin)

# Only game/* include dirs here — the framework's (runtime, generated, vendored backends, SDL, freetype)
# are inherited PUBLICly from the psxport link below.
target_include_directories(vagrant_port PRIVATE game game/core)

target_compile_options(vagrant_port PRIVATE -w -O2 -g
  ${SDL3_CFLAGS_OTHER} ${FREETYPE_CFLAGS_OTHER})

target_link_libraries(vagrant_port PRIVATE psxport)
