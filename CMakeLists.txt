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
  game/cd/ds_control.cpp
  game/cd/libds_field.cpp
  game/cd/native_file.cpp
  game/core/game_heap.cpp
  game/core/game_time.cpp
  game/core/resident_phase.cpp
  game/core/title_transfer.cpp
  game/input/pad_delivery.cpp
  game/render/battle_frame.cpp
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
endif()

# Break-first migration boundary: the generated-source product has been removed. The
# gameplay target remains unavailable until Vagrant Story is composed against
# psxport's dynarec-only executor and image-scoped native override API.
add_custom_target(vagrant_port
  COMMAND ${CMAKE_COMMAND} -E echo
          "Vagrant Story product unavailable: the title adapter to psxport's dynarec-only executor has not been implemented"
  COMMAND ${CMAKE_COMMAND} -E false
  VERBATIM)
