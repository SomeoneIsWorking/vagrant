---
id: 1
title: psxport_smoke cannot be built from a consumer tree (framework defect)
status: open
symptom: cmake -DPSXPORT_BUILD_SMOKE=ON in a game repo fails: 'Cannot find source file: tools/smoke/psxport_smoke.cpp' / 'No SOURCES given to target: psxport_smoke'
tags: framework,build,agnosticism
created: 2026-08-12
updated: 2026-08-12
---

Found 2026-08-12 while bootstrapping this repo, trying to run the framework's own agnosticism proof from a consumer tree.

CAUSE: external/psxport/cmake/psxport.cmake:237 is `add_executable(psxport_smoke tools/smoke/psxport_smoke.cpp)` — a RELATIVE source path. CMake resolves it against CMAKE_CURRENT_SOURCE_DIR, which for an `include()`d framework fragment is the CONSUMING game repo, not the framework. Every other framework path in that file already goes through ${PSXPORT_ROOT} (defined at line 47 from CMAKE_CURRENT_LIST_DIR); this one line does not.

CONSEQUENCE: the psxport_smoke link — the framework's stated proof that no game symbol is required — is only runnable from inside the psxport repo. A game repo cannot re-check agnosticism against the framework revision it actually builds. Affects spyro, spider1 and Tomba2Engine identically; nobody had tried it from a consumer tree.

FIX (one line, upstream, NOT made here — a game repo may not edit the framework):
  add_executable(psxport_smoke ${PSXPORT_ROOT}/tools/smoke/psxport_smoke.cpp)

WORKAROUND used here: none. -DPSXPORT_BUILD_SMOKE stays OFF (the default) and this repo's gate is the vagrant_seam OBJECT library, which compiles the seam TUs against the pinned framework headers.
