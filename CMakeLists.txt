cmake_minimum_required(VERSION 3.21)

project(vagrant_story_port LANGUAGES C CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

find_package(Python3 REQUIRED COMPONENTS Interpreter)
include(CTest)

# The framework owns image publication, invalidation and the Lightrec executor.
set(PSXPORT_DIR "${CMAKE_CURRENT_SOURCE_DIR}/external/psxport" CACHE PATH
    "psxport framework source directory (default: external/psxport)")
if(NOT EXISTS "${PSXPORT_DIR}/cmake/psxport.cmake")
  message(FATAL_ERROR "PSXPORT_DIR=${PSXPORT_DIR} has no cmake/psxport.cmake — resolve the psxport checkout")
endif()
set(PSXPORT_BUILD_TESTS OFF CACHE BOOL "" FORCE)
set(PSXPORT_BUILD_SMOKE OFF CACHE BOOL "" FORCE)
add_subdirectory("${PSXPORT_DIR}" framework EXCLUDE_FROM_ALL)

add_library(vagrant_runtime STATIC
  game/images/overlay_images.cpp)
target_include_directories(vagrant_runtime PUBLIC game)
target_link_libraries(vagrant_runtime PUBLIC psxport)

# Native owners that link and test without the process adapter.
add_library(vagrant_native STATIC
  game/boot/application.cpp
  game/boot/exec_title_tail.cpp
  game/boot/game_heap.cpp
  game/boot/game_time.cpp
  game/boot/guest_rect.cpp
  game/boot/resident_image.cpp
  game/boot/resident_phase.cpp
  game/cd/cd_command.cpp
  game/cd/ds_control.cpp
  game/cd/libds_field.cpp
  game/cd/native_file.cpp
  game/execution/dynarec_dispatch.cpp
  game/execution/guest_phase.cpp
  game/execution/native_owners.cpp
  game/images/battle_transfer.cpp
  game/images/title_entry.cpp
  game/images/title_transfer.cpp
  game/input/pad_delivery.cpp
  game/render/battle_frame.cpp
  game/render/battle_projection.cpp
  game/render/title_menu.cpp
  game/render/title_movie.cpp
  game/render/title_splash.cpp
  game/render/title_startup.cpp
  game/render/title_startup_recipe.cpp
  game/runtime/vagrant_context.cpp
  game/runtime/vagrant_runtime.cpp
  game/save/title_memcard_init.cpp
  game/save/title_save_check.cpp
  game/sync/frame_loop.cpp
  game/title/title_exec_phase.cpp)
target_include_directories(vagrant_native PUBLIC game)
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

  endif()

# The shipping product: one executable over the title adapter and psxport's dynarec-only executor.
add_executable(vagrant_port game/main.cpp)
target_link_libraries(vagrant_port PRIVATE vagrant_native)
