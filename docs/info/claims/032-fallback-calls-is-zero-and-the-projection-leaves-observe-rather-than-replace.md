---
id: C032
kind: claim
status: holds
created: 2026-09-28
tags: s015,dynarec,fallback,projection,superCall,display-area,cd-sync
depends: game/render/battle_projection.cpp, game/render/battle_projection.h, game/render/battle_projection_facts.h, game/core/dynarec_dispatch.cpp, game/core/native_owners.cpp, tools/re_viewport.py, tools/re_display_area.py, tools/re_vsync_sites.py, tests/test_battle_projection.cpp
---

## Claim

**The Vagrant Story product executes authenticated guest images through psxport's Lightrec executor
and interprets no guest block**, measured in a run that survived its first host field: 44,855 then
58,663 executed instructions, 430 then 617 translated blocks, and `fallback.calls = 0` with all
thirteen per-reason counters printed and zero. The title's boot is not merely executed but OWNED —
the four resident viewport leaves run again and the boot's own publication is measured through the
guest's leaf — and the first host field presents, black.

Four smaller claims hold with it, and each is stated separately because each can fail without the
headline failing: the projection owner's display-area cross-check now names the word the leaf itself
writes; the owner's four leaves observe rather than replace; the title's first presented field is the
boot's, not a title phase; and `CD_sync`'s budget exit is a title-side declaration gap rather than
the framework's in-segment clock.

## Evidence, and what each clause does NOT establish

| clause | evidence | what it does NOT establish |
|---|---|---|
| `fallback.calls == 0` over a scanned run | two independent sessions read the same numbers over the loopback surface; `executor_calls` 40 then 44, `translated_blocks` 430 then 617, `faults=0`, `refused_calls=0`, and all thirteen per-reason counters printed | that it stays 0 past the boot. 58,663 instructions is one and a half fields; the run ends in field 1 |
| the instrument RAN, rather than the zero being an absent tail | the executor counters beside it are nonzero and rising. The run-end line issue 0041 was blocked on carried `executor_calls=0`, which is "the instrument never ran"; this is not that | that a longer run would also read 0 — that is one command away, not yet taken |
| a publication's own horizontal extent is `env + 4` | `sh $a3, 4($v0)` at 0x8002B444 and `sh $s0, 4($s1)` at 0x8002B3B4, with `$s0 = addu $a3, $zero` in the delay slot at 0x8002B3A4; the height at `+6` from 0x8002B46C and 0x8002B3DC; and the run reads `8005E18C: 00E00140`, i.e. the halfword is 320 | that the address is a constant. It is the CALLER's `$a0` plus four, which is why no title constant can be the cross-check target |
| 0x8005DFD6 is BATTLE's rectangle and the resident never writes it | the reference census in `tools/re_display_area.py`: SLUS_010.40, TITLE.PRG and INITBTL.PRG name NONE of the four halfwords, and the only stores in any provisioned module are `func_800760CC`'s own four at 0x800761E0/E8/F0/0x80076200 | anything about a fourth overlay. ENDING.PRG carries the same function per the decompilation and is NOT provisioned here, so it is outside the census and the census says so |
| the four leaves observe rather than replace | `publishCentre`/`publishScreenDistance` perform the measured leaf through psxport's public GTE primitive; `publishDisplayArea` runs the original body through `dynarec::callOriginalToReturn` first. The GTE fixture seeds NOTHING and asserts CR24/CR25/CR26 and `projParams` all moved | that the widening is available. It is not, and `wideningBlocker()` is unchanged and still asserted |
| the first presented field is the boot's, and it is black | `scratch/run5/field0000.ppm` opened as PNG: a uniform featureless black rectangle; 0 of 71,680 pixels non-black, 1 distinct colour; and the same field's log carries `[gpu] display standard -> NTSC` | that a later field is black or not. The run ends in field 1, so no later phase was presented at all |
| `CD_sync`'s exit is a title-side gap, not the in-segment clock | `0x800324D8` has exactly ONE writer in the resident, `sb $v0, -0x1DB28($at)` at 0x80020D38, and `CD_sync` reads it at 0x80021000; `VagrantRuntime` declares no `guestCdStreamCallbackLayout`, so `cdReadyCallbackOwnedByGuestInterrupt()` is false. And the framework's `4a08ec55`/`5d4b3327` in-segment clock commit, rebuilt and re-run, changed nothing | that declaring the layout ends the wait. The slot address `CdReadyCallback` writes is not measured, and that is the named next step |
| the gate now asks about a subject in the execution path | `tools/verify.py` prints `0 of 3 retired-interpreter entry points` AND `2 of 2 Lightrec per-block interpreter entry points ARE linked … It is NOT a measurement of whether this title used one: that number is fallback.calls at run time` | that the link check answers S015. It does not, in either direction, and it now says so |

## What is explicitly still missing

Every TITLE phase. The run reaches the boot's first presented field and dies in field 1, so
S004's splash, the intro movie and the Start-skip menu are all unpresented, and no gameplay exists.
S015 is `partial` on the two clauses this claim establishes and `missing` on the rest; the wording
that carries that split is in `docs/project-state.md`, and the split is deliberate — "the
composition is correct and a frame presents" is not "the title executes authenticated images" and
this claim does not blur them.

## A PROCESS CONFLICT, recorded rather than papered over

`coord/claims/product-slot/claim.md` named a **CTR** agent (expires 2026-10-02) while this session's
brief named the slot mine until 2026-09-29T14:10. Per PROTOCOL.md an existing claim is not edited, so
the conflict is recorded here instead. The harm the protocol prevents is two product instances at
once, and that was checked immediately before each run: `ps -eo pid,etimes,args` showed no game
product running, and every run here was bounded (4 to 8 host fields), headless, silent, unpaced,
killed by the captured child PID, and written to this repository's gitignored `scratch/`. The CTR
claim was left exactly as found.

## What would falsify it

- A run reaching a later field with `fallback.calls > 0`. Then "dynarec-only" is false for this
  title, and the per-reason breakdown names which instruction class is unsupported — not this claim.
- `8005E18C` reading anything but 320 beside a log line showing the boot's publication. Then the
  leaf does not store the stated width at `+4`.
- A second `jal SetDefDispEnv` in the resident. Then the boot is not the only caller and the
  "one publication" reading of the fatal is wrong.
- The GTE fixture passing against an owner that writes no control register — which the new fixture's
  "seed nothing, read both destinations back" shape exists to make impossible.
- A declared `guestCdStreamCallbackLayout` leaving `CD_sync` spinning. Then the completion byte has a
  route this claim has not found and the single-writer census is a statement about `lui`-reachable
  references only; the census prints its method for that reason.
- The first presented field non-black on a machine that reaches a later phase. Then the black field
  was a present-timing artefact and not the field's content.
- A `Release` `vagrant_port` in which `lightrec_run_interpreter` is absent, or a different symbol
  set. Then claim 031's product-link reading was wrong in the other direction too.
