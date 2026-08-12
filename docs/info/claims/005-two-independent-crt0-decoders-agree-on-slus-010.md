---
id: C005
kind: claim
status: holds
created: 2026-08-12
tags: crt0
depends: game/core/game_config.cpp
---

## Claim

Two INDEPENDENT crt0 decoders agree on SLUS_010.40's whole boot group, so psxport's crt0_audit — the gate that now guards six ports' boot — is corroborated by a method that shares no code with it.

## Evidence

Measured 2026-08-12. vagrant tools/re_crt0.py CONCRETELY INTERPRETS the crt0 (52051 instructions from the PS-EXE header entry PC) and reports what execution did; psxport tools/crt0_extract (new, calls the same crt0_scan that runtime/recomp/crt0_verify.h::crt0_audit uses at boot) does SYMBOLIC straight-line decoding of 35 instructions. Different methods, no shared code. Both report, on the same bytes: bssZeroLo 0x80033678, bssZeroHi 0x800401A8, stackTopBase 0x80049138, stackTopBase2 0x8004913C, heapBase 0x800401A8, gp 0x80033674, libcInit 0x80026864, stack bias -8 (crt0_extract) == 'sp = mem[0x80049138] - 8' (re_crt0). ZERO disagreements on all 8 shared fields. re_crt0 additionally resolves heapSizePtr 0x80030FB8 / heapBasePtr 0x80030FB4 / gameMain 0x80042C38, and crt0_extract independently agrees on the two heap pointers. BOTH gates were then proven to go RED: 're_crt0.py --check-config' with kGp changed by one digit -> '[FAIL] gp SHIPPED 0x80033675 != MEASURED 0x80033674', 1 FAILED, rc=1; restored to md5 7dad10836314099ba6f891801d6bea84 and rc=0. (A first sabotage attempt was a NO-OP because the anchor text did not match, and its 0-FAILED result proved nothing — the applied one above is the real test.) psxport-side: 6 sabotages of crt0_boot.h/crt0_verify.h each red, restored at identical md5, 39/39 ctest.

## What would falsify it

a third decoder, or a booting vagrant port's own crt0_audit, disagreeing with either tool on any of these fields — agreement between two tools is not truth, and both could share a wrong assumption about PS-EXE header semantics
