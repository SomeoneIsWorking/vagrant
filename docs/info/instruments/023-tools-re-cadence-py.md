---
id: I023
kind: instrument
status: trusted
created: 2026-09-28
---

## Instrument

tools/re_cadence.py

## Validated by

SHA-bound cadence measurement of SLUS_010.40 plus all 3 provisioned overlays: VSync, its wait
helper and `vs_main_gametimeUpdate` each located by a `unique_shape` search rather than a typed
address; 368,826 words scanned, 63 accesses of `vs_gametime_tickspeed` matched, 10 of them
writers, closed rate domain {2,4}. Selftest 8/8, each negative shown red on its own subject: the
`a0==1` no-wait branch, the `(a0-1)` field count, the count-0 branch, the wait helper's `<<15`
countdown, VSync's shape anchor, the game clock's tickspeed load, an injected writer storing **5**
rejected by the `{2,4}` domain check, and a zeroed `BATTLE.PRG` store refused on the overlay
SHA-1. Registered as CTest `vagrant_cadence_selftest` and `vagrant_cadence`, both observed green.

## Known failure modes

The identity check sits UNDER every other negative, so a selftest asserting only "it refused"
would pass while testing SHA-1 seven times over. Every negative therefore asserts its refusal
names its own subject. This was a real intermediate defect here, caught by reading the refusal
text rather than its exit code.

The tickspeed load is a BYTE load (`lbu`, opcode 0x24) and the game-clock address is materialised
through a SHARED register (`lui $a1` then `addiu $a0,$a1`), so the shared `based_address` helper's
opcode and register rules apply to neither. Both are materialised explicitly, which is stricter
rather than looser because the register fields and the sign extension are all asserted. Routing
either through the shared helper raised, and the tool refused for the wrong reason.

`GAMETIME_SHAPE` deliberately EXCLUDES the tickspeed load. Folding it into the function's identity
turns one broken word into "the function cannot be found", which is a much weaker statement than
"the function is here and no longer reads the rate", and a selftest accepting either cannot tell
them apart.

Coverage: the decompilation declares 11 `.PRG` modules and only 3 are provisioned. The tool
REFUSES the entire report if any listed module fails its SHA-1, rather than censusing fewer
modules and reporting a domain that looks stronger for it.

The BATTLE writer at `0x80073468` stores a value not resolved to a literal within the 12-word
window. It is counted as **unresolved** and excluded from the domain claim, and it is the stated
falsifier in `docs/issues/0039`.
