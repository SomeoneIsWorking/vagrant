---
id: I010
kind: instrument
status: trusted
created: 2026-08-21
---

## Instrument

tests/test_launcher.py

## Validated by

2026-09-28, against the REWRITTEN launcher (16 checks). The previous validation note described
`execute()`, C11/C++20 compiler probes, and library preflights that the rewrite removed, so that
evidence no longer describes this file's subject and the note was corrected rather than appended to.

What the 16 checks actually cover now, and what each rules out:

| group | rules out |
|---|---|
| `LauncherRouteTest` (5) | a launcher that configures or builds after provisioning failed; a build failure that still launches; a configure failure that still builds; a route that never builds `vagrant_port`; a route that never launches it |
| `LauncherRefusalTest` (5) | a missing tool whose refusal does not name the install command; an unmapped platform whose refusal is not actionable; an absent framework accepted silently; an explicit `PSXPORT_DIR` ignored in favour of the symlink; provisioning that "succeeded" while an input was still absent |
| `EntryContractTest` (6) | help that provisions before exiting; `--prepare-only` that launches; a retired selector reachable from the launcher; drift in the frozen-uv shell/bootstrap/lock contract |

**The negative was shown red on its own subject, twice, for two different defects:**

1. The route's refusals originally printed through a `TextIO = sys.stderr` DEFAULT ARGUMENT, which
   binds the stream at definition time. `redirect_stderr` therefore captured nothing and
   `test_provisioning_refusal_names_the_stage_and_the_tool` failed with an empty buffer — a passing
   suite that could not have observed the refusal it claimed to assert. `run.py` now resolves
   `sys.stdout`/`sys.stderr` inside `main`.
2. The same test could be satisfied by a message the TEST ITSELF wrote, because it mocked
   `provision_inputs` with a side effect carrying the assertion's own words. It now drives the REAL
   `provision_inputs` with only the process boundary injected, and asserts the tool name that the real
   code formats.

Also verified: with the real measured inputs present, `missing_inputs()` returns empty, so the
"provisioning finished but inputs are absent" refusal is not vacuous on this machine.

## Known failure modes

- The route is composed and its refusals are gated; the route has NOT been executed end to end,
  because the workspace product slot was held (`docs/issues/0040`). A green suite here is evidence
  about the composition, not about a completed launch.
- `verify_product_link` (in `tools/verify.py`, not here) is the check that the LINKED product carries
  no interpreter. This file's retired-selector check is a SOURCE check and cannot establish that.
