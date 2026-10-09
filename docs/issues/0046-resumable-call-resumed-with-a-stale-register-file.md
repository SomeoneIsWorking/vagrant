---
id: 0046
title: A resumed guest call ran with another owner's registers
status: resolved
symptom: after a field boundary the suspended call continued with registers clobbered by host-side calls
tags: S004,S006,S013,title,cd
created: 2026-10-09
updated: 2026-10-09
---

`psxport/runtime/cpu/resumable_guest_call.cpp`: the R3000 register file was not saved at suspend nor restored on resume.

## Fix

Save at suspend, restore before each resume.

## Test

`tests/test_resumable_guest_call.cpp` in psxport.
