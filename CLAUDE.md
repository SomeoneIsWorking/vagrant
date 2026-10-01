# Vagrant Story — repository-specific instructions

This repository ports USA `SLUS_010.40` as a title-specific native/Lightrec consumer of
`external/psxport`. The CC0 `external/rood-reverse` decompilation is a source aid, not an authority
over the authenticated game bytes. Read `external/psxport/CLAUDE.md` for framework rules. Consult
`docs/project-goals.md` for intent, `docs/project-state.md` for current capability status,
`docs/codemap.md` for subsystem placement, `docs/issues/` for open defects and missing features, and
`docs/re-frontier.md` for the ordered binary evidence chain (`uv run --frozen python
tools/re_frontier.py next`).

## Execution and ownership

- The gameplay target uses a per-`Core` Lightrec executor for the authenticated resident executable
  and loaded `.PRG` images. Native overrides are image-and-address scoped; `superCall` executes the
  original guest body through Lightrec while suppressing only that override for the call. This
  title's gameplay target has no interpreter engine or selector; unsupported behavior fails at the
  exact guest PC. Static translation and generated guest code stay removed.
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
  is read against. psxport's executor counters are read from the executor, never restated.
- The overlays reuse EACH OTHER's bases, not the resident's: resident text ends at `0x80062000` and
  TITLE/BATTLE/ENDING load at `0x80068800`.
- Guest-rendered 4:3 is the fidelity baseline. Native BATTLE world rendering must derive from named
  pre-GTE camera, object, material, animation, and model state. Packet or OT replay cannot establish
  semantic widescreen or interpolation. Those enhancements have separate gates.

## Retail facts that constrain the work

- The horizontal projection word `vs_main_projectionDistance` (`0x8005E248`, setter `0x8007CCF0`) is
  gameplay state: BATTLE branches on it at `0x80074580` and `0x80074744`. Widen the canvas; never
  widen the word.
- The guest's 4:3 publication goes through four resident SDK leaves at `0x80041540` (`SetGeomOffset`),
  `0x80041534` (`SetGeomScreen`), `0x8002B374` (`SetDefDrawEnv`) and `0x8002B434` (`SetDefDispEnv`).
  Each leaf is observed after it runs, never replaced.
- The title presents 2 fields per game frame (30 fps) or 4 (15 fps), chosen at run time. 60 fps is
  structurally impossible, so interpolation is a presentation decision over matching source geometry.
- The boot's own display publication is 320x224 at `0x8005E18C`, stated by `_initScreen` at
  `0x80042054`. BATTLE's overlay rectangle at `0x8005DFD4` is zero BSS until BATTLE.PRG is loaded
  and is not a cross-check target during the boot.

## Running it

A boot field, a logo, a menu, an FMV and a clean trace are not gameplay conformance. The workspace
product slot is a single shared resource — check it before any run, never edit another agent's
claim, and never run a second product instance alongside another.

Verify borrowed addresses, offsets, fields, and load bases against SHA-bound title bytes before
shipping. The first migration discriminator is 1,000/1,000 host-owned TITLE fields from the exact
image with nonzero Lightrec execution, a reached native CD override, reached resident and TITLE
overrides, one scoped `superCall`, image-generation invalidation and an unchanged-generation
negative, zero guest-VSync violations, and independent CPU/device-state comparison.

Disc resolution is explicit argument, `PSXPORT_VAGRANT_DISC`, `.env`, then an unambiguous
repository-root CHD. Validate the resident executable and every loaded overlay. `external/psxport`
resolves to the workspace's live checkout, or a clone of its main where there is none; framework execution and HLE
changes belong there, while title identity and native behavior stay here.