---
id: I019
kind: instrument
status: trusted
created: 2026-08-24
---

## Instrument

tools/re_heap.py

## Validated by

2026-08-24: derives vs_main_initHeap 0x80043F74, heapA 0x800501A8, heapB 0x800501B8 from SLUS_010.40 by instruction shape (unique arena call site among 83,964 candidates; unique caller census). Selftest 5/5: destroyed call-site shape and capacity shift refuse with denominators, a duplicated caller is refused by the census, a +4 shipping constant is named by --check-source. It also caught its own author: the first expected store sequence put head B's final blockSz store at +0x38 where the image has `jr ra` — the real store is in the delay slot at +0x3C — and refused until corrected.

## Known failure modes

(none recorded yet)
