---
id: 25
title: Intro movie froze: continuous XA/STR reads delivered sectors but libcd completion never signalled
status: resolved
symptom: the game froze mid-intro-movie: a spin in resident 0x80022484 polling a 32-byte-slot result table (base 0x80039C48, index 0x80039C34)
tags: movie,cd,xa,boot,re-13
created: 2026-08-26
updated: 2026-08-26
---

Sectors flowed and were DMA3-copied continuously, so the guess that INT2 was never claimed was WRONG:
the capture showed IRQ2 raising, the title verifier seeing it and acking, per sector. Three defects
sat downstream — beginning with `Setmode STRSND` being ignored, so XA audio sectors polluted the data
FIFO.

**Dead ends:** attributing the freeze to a missing CD interrupt (it was raised and acked), and
treating continuous streaming as a file-read-shaped problem; RE-04's file-read completion route does
not cover a continuous STRSND read.
