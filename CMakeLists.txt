cmake_minimum_required(VERSION 3.21)

project(vagrant_story_port LANGUAGES C CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

find_package(Python3 REQUIRED COMPONENTS Interpreter)
include(CTest)

# The framework owns PS-X image publication, image generations, invalidation, and the Lightrec
# executor. This consumer only supplies title identity and behavior; it never grows a second cache.
set(PSXPORT_DIR "${CMAKE_CURRENT_SOURCE_DIR}/external/psxport" CACHE PATH
    "psxport framework source directory (default: external/psxport)")
if(NOT EXISTS "${PSXPORT_DIR}/cmake/psxport.cmake")
  message(FATAL_ERROR "PSXPORT_DIR=${PSXPORT_DIR} has no cmake/psxport.cmake — resolve the pinned psxport checkout")
endif()
find_package(Git REQUIRED)
execute_process(
  COMMAND "${GIT_EXECUTABLE}" -C "${PSXPORT_DIR}" rev-parse HEAD
  OUTPUT_VARIABLE PSXPORT_RESOLVED_SHA
  OUTPUT_STRIP_TRAILING_WHITESPACE
  ERROR_VARIABLE PSXPORT_REVISION_ERROR
  RESULT_VARIABLE PSXPORT_REVISION_RESULT)
string(LENGTH "${PSXPORT_RESOLVED_SHA}" PSXPORT_RESOLVED_LENGTH)
if(NOT PSXPORT_REVISION_RESULT EQUAL 0 OR NOT PSXPORT_RESOLVED_LENGTH EQUAL 40 OR
   NOT PSXPORT_RESOLVED_SHA MATCHES "^[0-9a-fA-F]+$")
  message(FATAL_ERROR "cannot identify PSXPORT_DIR=${PSXPORT_DIR}: ${PSXPORT_REVISION_ERROR}")
endif()
file(WRITE "${CMAKE_BINARY_DIR}/psxport_resolved.txt"
     "dir = ${PSXPORT_DIR}\ncommit = ${PSXPORT_RESOLVED_SHA}\n")
set(PSXPORT_BUILD_TESTS OFF CACHE BOOL "" FORCE)
set(PSXPORT_BUILD_SMOKE OFF CACHE BOOL "" FORCE)
add_subdirectory("${PSXPORT_DIR}" framework EXCLUDE_FROM_ALL)

add_library(vagrant_runtime STATIC
  game/core/overlay_images.cpp
  game/core/title_entry.cpp)
target_include_directories(vagrant_runtime PUBLIC game/core)
target_link_libraries(vagrant_runtime PUBLIC psxport)

# These authored native owners remain usable without the unavailable process adapter. Link their
# synthetic contracts against the same library the eventual title composition will consume.
add_library(vagrant_native STATIC
  game/core/vagrant_runtime.cpp
  game/core/application.cpp
  game/core/dynarec_dispatch.cpp
  game/core/execution_telemetry.cpp
  game/core/native_owners.cpp
  game/core/resident_image.cpp
  game/core/vagrant_context.cpp
  game/cd/ds_control.cpp
  game/cd/libds_field.cpp
  game/cd/native_file.cpp
  game/core/game_heap.cpp
  game/core/game_time.cpp
  game/core/resident_phase.cpp
  game/core/title_transfer.cpp
  game/input/pad_delivery.cpp
  game/render/battle_frame.cpp
  game/render/battle_projection.cpp
  game/render/title_menu.cpp
  game/render/title_movie.cpp
  game/render/title_splash.cpp
  game/render/title_startup.cpp
  game/render/title_startup_recipe.cpp
  game/save/title_memcard_init.cpp
  game/save/title_save_check.cpp
  game/sync/frame_loop.cpp)
target_include_directories(vagrant_native PUBLIC game game/core game/render)
target_link_libraries(vagrant_native PUBLIC psxport vagrant_runtime)

if(BUILD_TESTING)
  add_executable(vagrant_image_contract tests/test_vagrant_image_contract.cpp)
  target_link_libraries(vagrant_image_contract PRIVATE vagrant_native)
  add_test(NAME vagrant_image_contract COMMAND vagrant_image_contract)

  add_executable(vagrant_overlay_images tests/test_vagrant_overlay_images.cpp)
  target_link_libraries(vagrant_overlay_images PRIVATE vagrant_native)
  add_test(NAME vagrant_overlay_images COMMAND vagrant_overlay_images)

  add_executable(vagrant_title_entry tests/test_vagrant_title_entry.cpp)
  target_link_libraries(vagrant_title_entry PRIVATE vagrant_native)
  add_test(NAME vagrant_title_entry COMMAND vagrant_title_entry)

  add_executable(vagrant_ds_control_contract tests/test_ds_control_contract.cpp)
  target_link_libraries(vagrant_ds_control_contract PRIVATE vagrant_native)
  add_test(NAME vagrant_ds_control_contract COMMAND vagrant_ds_control_contract)

  add_executable(vagrant_game_heap tests/test_game_heap.cpp)
  target_link_libraries(vagrant_game_heap PRIVATE vagrant_native)
  add_test(NAME vagrant_game_heap COMMAND vagrant_game_heap)

  add_executable(vagrant_title_startup_recipe tests/test_title_startup_recipe.cpp)
  target_link_libraries(vagrant_title_startup_recipe PRIVATE vagrant_native)
  add_test(NAME vagrant_title_startup_recipe COMMAND vagrant_title_startup_recipe)

  add_executable(vagrant_native_runtime tests/test_vagrant_runtime.cpp)
  target_link_libraries(vagrant_native_runtime PRIVATE vagrant_native)
  add_test(NAME vagrant_native_runtime COMMAND vagrant_native_runtime)

  add_executable(vagrant_title_transfer tests/test_vagrant_title_transfer.cpp)
  target_link_libraries(vagrant_title_transfer PRIVATE vagrant_native)
  add_test(NAME vagrant_title_transfer COMMAND vagrant_title_transfer)

  add_executable(vagrant_battle_projection tests/test_battle_projection.cpp)
  target_link_libraries(vagrant_battle_projection PRIVATE vagrant_native)
  add_test(NAME vagrant_battle_projection COMMAND vagrant_battle_projection)

  add_executable(vagrant_dynarec_dispatch tests/test_dynarec_dispatch.cpp)
  target_link_libraries(vagrant_dynarec_dispatch PRIVATE vagrant_native)
  add_test(NAME vagrant_dynarec_dispatch COMMAND vagrant_dynarec_dispatch)

  add_test(NAME vagrant_projection_census_selftest
           COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/tools/re_projection.py"
                   --selftest)
  add_test(NAME vagrant_projection_census
           COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/tools/re_projection.py")

  # The BYTE census, which needs the provisioned images and so REFUSES without them. Registered
  # unconditionally on purpose: a tool that can only run on a provisioned machine must still be able
  # to fail on a machine that has one, and its selftest runs everywhere because it builds its own
  # mutated fixtures. The selftest is registered first because it is the one that must be green
  # wherever the gate runs.
  add_test(NAME vagrant_viewport_bytes_selftest
           COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/tools/re_viewport.py"
                   --selftest)
  add_test(NAME vagrant_viewport_bytes
           COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/tools/re_viewport.py")

  # THE VSync(n) CALL-SITE CENSUS, split out of re_viewport.py because it answers a different
  # question of the same image: what EVERY call site passes to one library routine, rather than what
  # ONE publication does. Same provisioning rule — both halves REFUSE (exit 2) without the images,
  # because a census that cannot see the image must say "not measured" and never print a zero. The
  # selftest is registered first and must be green wherever the gate runs.
  add_test(NAME vagrant_vsync_sites_selftest
           COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/tools/re_vsync_sites.py"
                   --selftest)
  add_test(NAME vagrant_vsync_sites
           COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/tools/re_vsync_sites.py")

  # THE RESIDENT'S DISPLAY-AREA PUBLICATION, and the word that IS one horizontal extent. Split out of
  # re_viewport.py because it is a different PUBLICATION: that tool measures BATTLE's overlay
  # publication, this one the boot's, and the first authenticated run of this title died because a
  # check written for the first was asked about the second (docs/issues/0042). The shared MIPS decoder
  # and the SHA-bound image loaders are imported, not copied, so the two agree on what an instruction
  # word means. Same provisioning rule: both halves REFUSE without the images.
  add_test(NAME vagrant_display_area_selftest
           COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/tools/re_display_area.py"
                   --selftest)
  add_test(NAME vagrant_display_area
           COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/tools/re_display_area.py")

  # The field-cadence census. It answers whether this 30 fps-title presents 30 or 60 fps, which
  # is what decides whether an interpolated 60 fps path is IN scope for it. Both the selftest
  # and the census need the provisioned images and all three overlays, so both REFUSE (exit 2)
  # without them rather than reporting a rate: a cadence tool that cannot see the image must
  # say "not measured", never a number. The selftest is registered first and must be green
  # wherever the gate runs; it builds its own mutated fixtures in memory, so it needs no
  # writable scratch and no second copy of the image.
  add_test(NAME vagrant_cadence_selftest
           COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/tools/re_cadence.py"
                   --selftest)
  add_test(NAME vagrant_cadence
           COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/tools/re_cadence.py")
endif()

# THE SHIPPING PRODUCT. One executable over the title adapter and psxport's dynarec-only executor.
# There is deliberately no second target, no engine selector, and no build rule that can produce
# guest code as a host object: the product is this binary or it does not exist.
add_executable(vagrant_port game/main.cpp)
target_link_libraries(vagrant_port PRIVATE vagrant_native)

# THE LIVE PIN CHECK. Not a selftest: this runs the real function against this repository's real
# psxport.pin and the real build receipt, so it can fail when the pin is actually wrong.
#
# MEASURED 2026-09-27: every port in the workspace registered only a SELFTEST of the check function, run
# against a temporary fixture. A selftest asserts the function behaves; it cannot fail when this repo's
# pin is stale, which is why ten ports reported green while four pins were demonstrably stale. --build
# points at THIS build directory, configured moments ago, so the receipt is current by construction and
# the staleness guard cannot fire spuriously. Verified: perturbing psxport.pin turns it red.
if(BUILD_TESTING)
  add_test(
    NAME vagrant_psxport_pin_live
    COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/tools/psxport_sync.py"
            --check --build "${CMAKE_BINARY_DIR}")
endif()

# The pin tool's own behaviour: the staleness guard, and a bump that records the commit the build
# RESOLVED rather than the framework's current HEAD. Added because 7 of 10 ports shipped the tool with no
# test gating it at all. Unguarded on purpose where this repository does not define BUILD_TESTING -- a
# guarded add_test there is silently inert, which is the failure this gate exists to prevent.
add_test(
  NAME vagrant_psxport_pin_selftest
  COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/tests/test_psxport_sync.py")
