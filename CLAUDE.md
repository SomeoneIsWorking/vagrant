# Vagrant Story — repository-specific instructions

This repository ports USA `SLUS_010.40` as a title-specific native/Lightrec consumer of
`external/psxport`. The CC0 `external/rood-reverse` decompilation is a source aid, not an authority
over the authenticated game bytes. Read `external/psxport/CLAUDE.md` for framework rules. Consult
`docs/project-goals.md` for intent, `docs/project-state.md` for current capability status,
`docs/re-frontier.md` for ordered binary evidence, `docs/issues/` for atomic work, and
`docs/codemap.md` for subsystem placement. Historical native or generated-source runs recorded in
those docs are not Lightrec gameplay evidence.

## Execution and ownership

- The gameplay target uses a per-`Core` Lightrec executor for the authenticated resident executable
  and loaded `.PRG` images. Native overrides are image-and-address scoped; `superCall` executes the
  original guest body through Lightrec while suppressing only that override for the call. This
  title's gameplay target has no interpreter engine or selector; unsupported behavior fails at the
  exact guest PC. Preserve the completed removal of static translation and generated guest code.
- Address alone cannot identify an overlay block: BATTLE, TITLE, and ENDING reuse `0x80068800`, and
  other modules reuse further load bases. Image generation must participate in translation and
  override identity. Overlay loads, guest writes, DMA, savestate restore, and override changes
  invalidate affected execution decisions. psxport owns Lightrec integration, CPU/device sync,
  executable memory, and cache mechanics; this repository owns image identity and title behavior.
- `VagrantRuntime` supplies the measured `GuestProgramImage`, the measured VSync `PlatformHlePlan`,
  the per-Core `VagrantFrameDriver`, and the resident publication boundary. It must not absorb their
  implementations. `vagrant::Application` is the process composition owner and the only place that
  knows the ORDER the machine becomes a product; it composes and does not implement.
- `vagrant::dynarec` (`game/core/dynarec_dispatch.{h,cpp}`) is the ONLY module here that resolves an
  image identity, spells an `ExecutionBudget`, or chooses a dispatch form. Add nothing that does any
  of those three elsewhere. `vagrant::installResidentNativeOwners` decides WHICH leaves the title owns
  and is reached from the image publication boundary, never from `registerOverrides` — which runs
  before any image exists and therefore cannot resolve an address to a generation.
- Native CD work must preserve retail command postconditions where the synchronous host CD model
  cannot deliver required asynchronous callbacks. Do not bypass a wait by writing its timer or
  phase. `NativeFile` owns authenticated extents; title memcard transfers preserve their measured
  allocation, image, upload, reset, and event lifecycle.
- A new execution counter belongs in `game/core/execution_telemetry.{h,cpp}` with the denominator it
  is read against. A counter whose zero cannot be distinguished from "the instrument never ran" does
  not belong there. psxport's executor counters are read from the executor, never restated.
- The overlays reuse EACH OTHER's bases, not the resident's: resident text ends at `0x80062000` and
  TITLE/BATTLE/ENDING load at `0x80068800`. An override retirement claim that says otherwise is
  refuted by `tools/re_overlay.py`, and one such claim was already written and withdrawn.
- Guest-rendered 4:3 is the fidelity baseline. Native BATTLE world rendering must derive from named
  pre-GTE camera, object, material, animation, and model state. Packet or OT replay cannot establish
  semantic widescreen or interpolation. Those enhancements have separate gates.

## Verification and inputs

AUTHENTICATED RUNS HAVE HAPPENED, and they are still not a title phase. On 2026-09-28 a run
authenticated the resident image, executed it through Lightrec, and read `fallback.calls = 0` with
every per-reason counter zero beside nonzero executor counters — so S015 is `partial` on the two
clauses that establishes and `missing` on the rest. The run presents the BOOT's first field, which is
black, and then ends in field 1 inside libcd's `CD_sync`. **A boot field, a logo, a menu, an FMV and
a clean trace do not establish gameplay conformance**, and `docs/issues/0040` separates an adapter
from a run while `docs/issues/0042` separates a boot field from a title phase. The workspace product
slot is a single shared resource — check `$PSX/coord/claims/product-slot/claim.md` before any run,
never edit another agent's claim, and never run a second product instance alongside another.

The first migration discriminator is 1,000/1,000 host-owned TITLE fields from the exact image with
nonzero Lightrec execution, a reached native CD override, reached resident and TITLE overrides,
one scoped `superCall`, image-generation invalidation and an unchanged-generation negative, zero
guest-VSync violations, and independent CPU/device-state comparison. Then exercise representative
interactive BATTLE gameplay and released-host behavior. `docs/project-goals.md` and
`docs/project-state.md` own the detailed success conditions and current gap.

Verify borrowed addresses, offsets, fields, and load bases against SHA-bound title bytes before
shipping. Start non-trivial work with `uv run --frozen python tools/info.py brief <terms>`,
`uv run --frozen python tools/re_frontier.py next`, and
`uv run --frozen python tools/catalog.py search <symptom>`.

Disc resolution is explicit argument, `PSXPORT_VAGRANT_DISC`, `.env`, then an unambiguous
repository-root CHD. Validate the resident executable and every loaded overlay. `external/psxport`
resolves to the shared checkout or a private clone at `psxport.pin`; framework execution and HLE
changes belong there, while title identity and native behavior stay here.
