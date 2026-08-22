---
id: I017
kind: instrument
status: trusted
created: 2026-08-22
---

## Instrument

tools/re_title_movie.py measures TITLE's RGB24 MDEC callback and display contract from SHA-bound retail bytes

## Validated by

2026-08-22: pristine TITLE.PRG derives callback/data/display owner and gates shipping constants; three negatives independently destroy the callback LoadImage call, shift the shipping frameComplete address, and mutate overlay identity, and all are refused with denominators.

## Known failure modes

This is a static contract instrument: it does not decode a frame, prove runtime callback delivery, or
prove that a native presentation contains coherent pixels. C021 therefore pairs it with a real-disc
same-index positive/producer-disabled negative visual discriminator.
