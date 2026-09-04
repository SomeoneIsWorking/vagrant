cmake_minimum_required(VERSION 3.21)

project(vagrant_story_port LANGUAGES NONE)

# Break-first migration boundary: the generated-source product has been removed. The
# gameplay target remains unavailable until Vagrant Story is composed against
# psxport's dynarec-only executor and image-scoped native override API.
add_custom_target(vagrant_port ALL
  COMMAND ${CMAKE_COMMAND} -E echo
          "Vagrant Story product unavailable: the title adapter to psxport's dynarec-only executor has not been implemented"
  COMMAND ${CMAKE_COMMAND} -E false
  VERBATIM)
