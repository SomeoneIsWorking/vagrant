---
id: 22
title: Cross-overlay call target demoted to a local label
status: resolved
symptom: INITBTL's direct call to BATTLE 0x800E6EAC had no dispatcher entry
tags: overlay,battle,routing,re-15
created: 2026-08-24
updated: 2026-08-24
---

Entry demotion protects internal call targets only within one image, so BATTLE's own branch to
`0x800E6EAC` kept only `L_800E6EAC` and the separate callable entry was discarded — even though the
SHA-bound BATTLE word there is `jr ra` with `lui t0,0x800F` in its delay slot, and rood-reverse
independently labels it `func_800E6EAC`.

**Dead end:** adding a game seed. The failure was in how one image's internal-entry rule met a
cross-image target, which is why target protection now spans images.
