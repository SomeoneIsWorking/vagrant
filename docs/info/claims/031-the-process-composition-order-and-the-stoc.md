---
id: C031
kind: claim
status: holds
created: 2026-09-28
tags: s015,dynarec,run-evidence,platform-hle,composition-order,product-link
depends: game/core/application.cpp, game/core/vagrant_runtime.cpp, game/sync/vsync_facts.h, tools/re_vblank.py
---

## Claim

The Vagrant Story product's PROCESS COMPOSITION ORDER is correct, its image-scoped native leaves are
registered from exactly one boundary, its `PlatformHlePlan` declares every stock hardware-service
leaf the boot actually reaches, and the boot now reaches its first presented host field on the
authenticated image — where it stops on a NAMED disagreement inside the projection owner rather than
on an unbounded guest wait.

Each clause is a composition claim. None of them is a claim that the title plays, and none of them
is a claim that a guest block was translated rather than interpreted.

## Evidence, and what each clause does NOT establish

| clause | evidence | what it does NOT establish |
|---|---|---|
| The runtime is installed before the first `Core` | `tools/run.py --prepare-only` builds; a headless run reaches `authenticated resident image: … image 1/1`. Before the fix the same run died at `Game construction did not create this Core's VagrantContext` | that any guest code executed; that run had `executor_calls=0` |
| The native-leaf table has ONE registration call site | `resident native owners registered against image 1/1: 1 allocator leaf + 4 measured projection publication leaves` with no refusal. Before the fix the same run produced `refused duplicate override 'Vagrant vs_main_initHeap' … owned by 'Vagrant vs_main_initHeap'` — a duplicate key, because `Application::start` re-ran the table `loadResidentImage` had already installed | that any leaf was INVOKED; the run-end census that answers that is still unreachable |
| Every stock hardware-service leaf the boot reaches is declared | `plat-hle: 3 direct-runtime hardware services installed` — `VSync` with its measured query counter, plus `CD_cw` and `CD_sync` from `game/cd/cd_facts.h`. Before the fix it was `1 direct-runtime hardware services installed` and the boot's first field spun in `CD_sync` until `budget-exhausted at 0x8002105C after 564502 cycles` | that the synchronous CD model preserves guest libds state — `stockCdWorkArea` is deliberately zero because this title has NOT measured the libcd `CdLastPos` / last-mode bytes |
| The boot reaches a presented first host field | `entering the bounded Vagrant Story product loop`, `dbgsrv listening on 127.0.0.1:5949`, `gpu_vk present image 960x720 (headless sink)`, in that order, and then the owner refuses | that the frame has any CONTENT. No `shot` was taken, because `shot` needs the control surface that this same field does not reach. This is a present, not a picture |
| The new measured constant is SHA-bound, not typed | `tools/re_vblank.py --check-source --selftest` → `4/4 PASS`, with a NEGATIVE case that perturbs `kVSyncQueryCounter` by +4 and requires the refusal to name it | that the counter is the only field counter in the image — the instrument cross-checks it against VSync's query, wait and completion paths, `startIntrVSync` and the resident VBlank handler |
| The gate | 18/18 CTest. `clang-format` 0 violations (56 at the baseline commit `9eb8b55`) and 13 clang-tidy findings (a large pre-existing debt at the same baseline), none of them in the code this claim adds | that the style stages were ever green: the brief's "17/18" was about CTest only, and "18/18" read as a green gate would be wrong |

## The measured negative that came out of the run, and it is about an INSTRUMENT

`tools/verify.py::verify_product_link` prints `product link: 0 of 3 interpreter entry points present
in the shipped executable`, and S002 leans on it in its strongest terms. `nm -C` on the SAME binary
reports `lightrec_run_interpreter` (`0x722a30 T`) and `lightrec_emit_jump_to_interpreter`
(`0x736940 T`). The three symbols it looks for belong to the interpreter psxport RETIRED; the
interpreter this product contains is Lightrec's own per-block interpreter, which is exactly what
`fallback.calls` counts. The check is green because it asks about a component outside the execution
path.

This belongs in a claim rather than only in an issue because it is a statement about what this
repository's gates can and cannot establish, and a green gate is the kind of thing that gets
inherited. **Until that check is pointed at a subject in the execution path, "the product links no
interpreter" is not established for this title by anything in the tree, and `fallback.calls` in a
real run is the only possible answer** — in either direction. A link check cannot answer it.

## What is explicitly still missing

`fallback.calls` itself. It is UNMEASURED, and the `fallback_blocks=0` the product prints at
shutdown carries `executor_calls=0`, so it is "the instrument never ran" and not "scanned and found
none". The run-end report is only reached when the `for (frame = 0;; ++frame)` loop ends, and the
product aborts inside field 0; the live `guest` reading needs one serviced frame, and
`DbgServer::service` runs AFTER `shell.step` in this title's spine. See
`docs/issues/0041-the-title-ran-four-real-defects-stood-between.md`.

## What would falsify it

- A run of the current tree that gets past `SetDefDispEnv` and dies somewhere else, with no
  projection-owner refusal. Then the owner's premise was right and the boot's own publication is the
  defect, which is upstream of everything here.
- A `Release` `vagrant_port` with no `lightrec_run_interpreter` symbol. Then this claim's reading of
  the link check is wrong, and S002 needs re-deriving from the binary rather than from the check.
- `PSXPORT_LIGHTREC_FALLBACK_BLOCK_LIMIT` changing, or the framework refusing a fallback with a
  `threshold-exceeded` line in a run. Either would mean the bounded-fallback bound quoted in issue
  0041 is not the bound in force.
- A second call site for `installResidentNativeOwners`, or a second `psxport_install_game`. Either
  reintroduces a duplicate key or a null `Core` runtime, which is the shape of the two fatals above.
- `stockCdWorkArea` staying zero while a run shows retail libds `Setloc`/`Setmode` state diverging.
  That would make the zero a real defect rather than the documented unmeasured default.
