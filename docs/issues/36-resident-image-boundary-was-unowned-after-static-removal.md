---
id: 36
title: The resident image boundary was unowned after static removal
status: resolved
symptom: removing the static launcher's generated boot path left gameplay unavailable because no title code claimed the resident header contract
tags: resident,image,re-02
created: 2026-08-27
updated: 2026-08-27
---

`vagrant::VagrantRuntime::loadResidentImage` checks the measured `SLUS_010.40` PS-X header before
delegating to psxport's `loadPsxExeImage`, so the framework stays the sole owner of image catalog
generations, invalidation and memory publication.

**Dead end:** the title re-deriving the file's SHA-1. That is `tools/extract_exe.py`'s rule and a
second hash would be a second answer to "are these this title's bytes".
