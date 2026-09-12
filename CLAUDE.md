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
- `VagrantRuntime` composes `VagrantFrameDriver`, resident and TITLE phases, CD owners, pad delivery,
  title producers, native heap behavior, and BATTLE peers. It must not absorb their implementations.
  `VagrantFrameDriver` owns finite fields; guest VSync `0x8001F6C4` is fatal outside that boundary.
- Native CD work must preserve retail command postconditions where the synchronous host CD model
  cannot deliver required asynchronous callbacks. Do not bypass a wait by writing its timer or
  phase. `NativeFile` owns authenticated extents; title memcard transfers preserve their measured
  allocation, image, upload, reset, and event lifecycle.
- Guest-rendered 4:3 is the fidelity baseline. Native BATTLE world rendering must derive from named
  pre-GTE camera, object, material, animation, and model state. Packet or OT replay cannot establish
  semantic widescreen or interpolation. Those enhancements have separate gates.

## Verification and inputs

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
