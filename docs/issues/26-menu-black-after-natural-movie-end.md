---
id: 26
title: Menu black after the movie ends naturally
status: resolved
symptom: stored black captures were read as a black title menu after the natural (no-input) movie end
tags: title,render,evidence,re-13
created: 2026-08-26
updated: 2026-08-26
---

Not a bug: those captures occur after the recorded input left the idle path and after the renderer
switched from TITLE (512x224) to BATTLE (320x224). The "menu frame" CSV held 24-primitive BATTLE/loading
batches — black polygons, item sprites on BATTLE CLUT coordinates — not TITLE's 1,400-sprite menu. The
frames that visibly show the menu came from `vs-skip.pad`/`vs-drive.pad`, which are valid skip controls
and not natural controls.

**Dead end worth remembering:** a black capture is not evidence of a defect until the replay is checked
for what it actually pressed, and the display mode is checked for which module presented it.
