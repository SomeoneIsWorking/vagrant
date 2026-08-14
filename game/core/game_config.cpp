// game_config.cpp — the Vagrant Story (SLUS_010.40, USA) GameConfig: the guest-address literals the
// PSX-generic framework reads through `c->cfg->field`.
//
// READ THIS BEFORE FILLING ANYTHING IN.
//
// **Exactly TWO groups are filled in: the crt0/boot group (RE-01) and the three measured overlay
// slots (RE-03). Every other address here is still ZERO because it has not been reverse-engineered.**
// Zero is the
// honest value and it is deliberate: psxport fails fast on a zero it needs, whereas a
// plausible-looking WRONG address does not fail cleanly — it breaks boot or diverges the byte-compare
// in a way that reads as a framework bug. Each group names the open step in docs/re-frontier.md.
//
// A CC0 matching decompilation of this exact executable exists and names 813 symbols in it
// (external/rood-reverse, docs/references.md; its SLUS_010.40 target is byte-identical to the image
// this repo extracts — verified 21/21 modules by tools/verify_decomp_targets.py). It is therefore an
// excellent way to LOCATE a value fast. It is NOT a substitute for measuring one: a value copied out
// of it is a REFERENCE until this repo has confirmed it against these bytes, and the standing rule in
// this workspace is that where a reference and a measurement disagree, the measurement wins. When you
// fill a field, add the measurement and a shipping-value gate; a plausible citation alone is not a
// discriminator.
#include "game_iface.h"

// MEASURED, from the PS-EXE header of the extracted SLUS_010.40 (tools/extract_exe.py prints it) and
// from the disc's SYSTEM.CNF.
//
//   PS-X EXE  pc0 = 0x8001F544   text = 0x80010000 + 0x52000   sp = 0x801FFFF0   gp0 = 0 (crt0 sets gp)
//               d_size = 0   b_addr = 0   b_size = 0   ->  the LOADER clears no .bss and sets no gp;
//               both are crt0's job, which is why RE-01 had to execute crt0 rather than read a header
//   SYSTEM.CNF  BOOT = cdrom:\SLUS_010.40;1   STACK = 801fff00   TCB = 4   EVENT = 16
//
// NOTE, because it looks like a contradiction: crt0 does NOT use the header's s_addr (0x801FFFF0) or
// SYSTEM.CNF's STACK (0x801FFF00) for the stack. It computes sp from the guest global `_ramsize`
// (0x80049138 = 0x00200000) minus 8, i.e. sp = fp = 0x801FFFF8 — measured, see tools/re_crt0.py. The
// header/CNF values are what the BIOS shell sets up before jumping to the entry point; crt0 then
// overwrites it. Do not "fix" the boot group to agree with the header.
static constexpr uint32_t kPsExeEntry     = 0x8001F544u;   // header pc0
static constexpr uint32_t kPsExeTextAddr  = 0x80010000u;   // header t_addr
static constexpr uint32_t kPsExeTextSize  = 0x00052000u;   // header t_size
static_assert(kPsExeEntry >= kPsExeTextAddr &&
              kPsExeEntry < kPsExeTextAddr + kPsExeTextSize,
              "the PS-EXE entry must lie inside the loaded text — if this fires, the header was "
              "misread and every number in this file's comment block is suspect");

// ─────────────────────────────────────────────────────────────────────────────────────────────────
// RE-01, MEASURED 2026-08-12 by EXECUTING crt0 on the extracted SLUS_010.40 (sha1 fababcf…) — not read
// out of a reference. `python3 tools/re_crt0.py` reproduces every value below; the tool starts at the
// PS-EXE header's own entry PC and reports what the execution DID — every store, every load, both
// calls. rood-reverse's symbol names appear below as corroborating LABELS only.
//
// **THE ELEVEN CONSTANTS BELOW ARE GATED AGAINST THE BYTES, and that is new.** `re_crt0.py
// --check-config` parses this file's `kXxx` constants AND the designated initialisers that bind them
// to GameConfig fields, and diffs them against what it measures from the executable. Before that
// existed, the tool kept its own `FIXTURE_EXPECT` copy and this file kept a second hand-typed copy
// with nothing comparing them: moving `kHeapSizePtr` +4 and pointing `kLibcInit` at an unrelated nop
// passed BOTH gates (workspace PROTOCOL.md, "THE SHIPPED VALUE MUST BE COMPARED TO THE MEASURED ONE").
// The tool no longer holds a copy — this file is the fixture, and `--selftest` proves the red path by
// mutating this text and requiring a report.
//
// The disassembly block below is GENERATED for the same reason one level down: its hand-typed
// predecessor had three raw words that did not match the executable (0x8001F548 read `24427836` for a
// real `24423678`), presented as an audit trail, and nothing checked it. Regenerate with
// `--emit-citations`; `--gate-citations` regenerates it and fails on any difference.
//
// >>> BEGIN GENERATED CITATIONS — generated from the executable by `python3 tools/re_crt0.py
//     --emit-citations`, and gated by `--gate-citations`, which regenerates this block and
//     FAILS unless it is byte-identical to what is below. DO NOT HAND-EDIT: the hand-typed
//     predecessor had three raw words that did not match the bytes (0x8001F548 read
//     `24427836` for a real `24423678`), and nothing checked it. The arrows name the
//     constants the measurement attributed to each line — they are emitted, not typed.
//   sha1 fababcfd4325d42f350d95b3472874affeb0e48c   entry 0x8001F544   42 instructions
//   8001F544  3c028003  lui $v0, 0x8003
//   8001F548  24423678  addiu $v0, $v0, 0x3678
//   8001F54C  3c038004  lui $v1, 0x8004
//   8001F550  246301a8  addiu $v1, $v1, 0x1a8
//   8001F554  ac400000  sw $zero, 0x0($v0) <- kBssZeroLo, kBssZeroHi
//   8001F558  24420004  addiu $v0, $v0, 0x4
//   8001F55C  0043082b  sltu $at, $v0, $v1
//   8001F560  1420fffc  bne $at, $zero, 0x8001F554
//   8001F564  00000000  nop
//   8001F568  3c028005  lui $v0, 0x8005
//   8001F56C  8c429138  lw $v0, -0x6ec8($v0) <- kStackTopBase
//   8001F570  00000000  nop
//   8001F574  2042fff8  addi $v0, $v0, -0x8
//   8001F578  3c088000  lui $t0, 0x8000
//   8001F57C  0048e825  or $sp, $v0, $t0
//   8001F580  3c048004  lui $a0, 0x8004
//   8001F584  248401a8  addiu $a0, $a0, 0x1a8
//   8001F588  000420c0  sll $a0, $a0, 3
//   8001F58C  000420c2  srl $a0, $a0, 3
//   8001F590  3c038005  lui $v1, 0x8005
//   8001F594  8c63913c  lw $v1, -0x6ec4($v1) <- kStackTopBase2
//   8001F598  00000000  nop
//   8001F59C  00432823  subu $a1, $v0, $v1
//   8001F5A0  00a42823  subu $a1, $a1, $a0
//   8001F5A4  3c018003  lui $at, 0x8003
//   8001F5A8  ac250fb8  sw $a1, 0xfb8($at) <- kHeapSizePtr
//   8001F5AC  00882025  or $a0, $a0, $t0
//   8001F5B0  3c018003  lui $at, 0x8003
//   8001F5B4  ac240fb4  sw $a0, 0xfb4($at) <- kHeapBase, kHeapBasePtr
//   8001F5B8  3c018003  lui $at, 0x8003
//   8001F5BC  ac3f3678  sw $ra, 0x3678($at)
//   8001F5C0  3c1c8003  lui $gp, 0x8003
//   8001F5C4  279c3674  addiu $gp, $gp, 0x3674
//   8001F5C8  03a0f021  addu $fp, $sp, $zero
//   8001F5CC  0c009a19  jal 0x80026864     <- kLibcInit
//   8001F5D0  20840004  addi $a0, $a0, 0x4
//   8001F5D4  3c1f8003  lui $ra, 0x8003
//   8001F5D8  8fff3678  lw $ra, 0x3678($ra)
//   8001F5DC  00000000  nop
//   8001F5E0  0c010b0e  jal 0x80042C38     <- kGameMain
//   8001F5E4  00000000  nop
//   8001F5E8  0000004d  break
// <<< END GENERATED CITATIONS
//
// Reading the block: the clear loop is 0x8001F554..0x8001F560 (13,004 word stores, 52,016 bytes,
// [0x80033678,0x800401A8)); sp = fp = 0x801FFFF8 comes from 0x8001F56C/74/7C and is NEITHER the
// header's s_addr NOR SYSTEM.CNF's STACK; the heap size 0x001BBE50 is computed at 0x8001F59C/A0; and
// the `break` at 0x8001F5E8 is why main never returns, as psxport assumes.
//
// FOUR things measured here that a reader will otherwise re-derive, and the third CORRECTS an earlier
// version of this comment that was wrong:
//
// 1. THE CLEAR RANGE COULD ONLY COME FROM THE LOOP. The PS-EXE header has b_addr = b_size = 0, so
//    there is no declared .bss: the file is 337,920 bytes = a 2,048-byte header plus a 335,872-byte
//    (83,968-word) image loaded verbatim at [0x80010000,0x80062000). Independent cross-check:
//    [0x80033678,0x800401A8) is 52,016 bytes and ALL ZERO in that image, while the 120 bytes
//    immediately BELOW 0x80033678 hold 44 non-zero bytes — so the low bound is a real boundary, not an
//    arbitrary address. That second half is the point: "the range is all zero" alone would also hold
//    for a range picked too large.
// 2. `kLibcInit` IS A BIOS THUNK, NOT A LINKED ROUTINE. 0x80026864 is `addiu $t2,$zero,0xa0 / jr $t2 /
//    addiu $t1,$zero,0x39` — a tail jump into the BIOS A0 table, function 0x39 = InitHeap(addr, size).
//    psxport HLEs exactly that (runtime/recomp/hle.cpp, `case 0x39: heapInit(a0, a1)`), so it needs
//    BOTH argument registers. The shared `crt0_apply` now supplies both (`a0` and `a1`); issue #3
//    records the former missing-a1 framework defect and its regression gate.
// 3. **THIS IMAGE IS THREE SEPARATELY-LINKED SEGMENTS, AND 0x800401A8 IS THE END OF THE FIRST ONE'S
//    .bss — NOT the end of the image.** An earlier version of this block said "the heap starts where
//    .bss ends" full stop, which reads as "the heap is free RAM" and is FALSE. The arena crt0 declares
//    is [0x800401AC,0x801FBFFC); it overlaps the loaded image over [0x800401AC,0x80062000) = 138,836
//    bytes, of which 45,761 are non-zero — and `kGameMain` 0x80042C38 and the `_ramsize`/`_stacksize`
//    globals 0x80049138/0x8004913C are all INSIDE it. Measured layout (zero/non-zero profile of the
//    image; rood-reverse's splat config supplies the labels and agrees to the byte):
//        [0x80010000,0x80033678)  segment 1  .rodata/.text/.data   94,803 non-zero bytes
//        [0x80033678,0x800401A8)  segment 1  .sbss + .bss          all zero  <- crt0 clears THIS
//        [0x80040210,0x80041D68)  segment 2  libgte .rodata/code    5,912 non-zero
//        [0x80041D68,0x8004FF88)  segment 3  `main` .rodata/code/.data  39,849 non-zero
//        [0x8004FF88,0x80062000)  segment 3  `main` .bss           all zero, and crt0 NEVER clears it
//                                                                  (the verbatim load supplies the
//                                                                   zeros, which is why b_size = 0
//                                                                   works for this image)
//    Independent confirmation that 0x800401A8 is segment 1's boundary and NOT the image's: the SN
//    startup object keeps the linker's own record as initialised data at 0x80030FBC — __text
//    0x80010AA4+0x1EA90 -> 0x8002F534 = __data, __data+0x4140 -> 0x80033674 = `kGp`, __bss
//    0x80033680+0xCB28 -> 0x800401A8 = `kBssZeroHi`. That is link-time metadata rather than crt0's
//    instruction stream, so it is a genuinely second source for two of the eleven values, and it
//    describes only 0x80010AA4..0x800401A8. re_crt0.py asserts all three identities.
// 4. **THE BIOS HEAP IS NEVER ALLOCATED FROM, which is why (3) is not a contradiction.** Census over
//    the whole image (re_crt0.py, 2,023 `jal` sites against 19 BIOS A0 thunks): the ONLY heap-related
//    A0 thunk present at all is InitHeap 0x80026864, and its only caller is crt0 itself at
//    0x8001F5CC. There is no malloc/free/calloc/realloc thunk in the image, so no code in it can
//    reach one. The game allocates from its own allocator instead (rood-reverse: `vs_main_initHeap`
//    0x80043F74, called with an arena at 0x8010C000 + 0xF2000 — above the image's 0x80062000 end).
//    So the overlapping BIOS arena is inert stock-crt0 boilerplate, on real hardware exactly as here;
//    it is NOT evidence that a value was mismeasured. What it does mean is that this game cannot be
//    used to demonstrate psxport's BIOS heap working — see docs/issues/0003.
//
// These are named constants used ONCE in the struct below and re-used by the static_asserts under it.
// Naming them is what lets those asserts be real: an assert written over two literal copies of the
// same value is a check that can never fire, which is the shape of a lying diagnostic.
static constexpr uint32_t kBssZeroLo     = 0x80033678u;   // __ra_temp — first word the loop clears
static constexpr uint32_t kBssZeroHi     = 0x800401A8u;   // exclusive end of the clear loop
static constexpr uint32_t kStackTopBase  = 0x80049138u;   // _ramsize   global (holds 0x00200000)
static constexpr uint32_t kStackTopBase2 = 0x8004913Cu;   // _stacksize global (holds 0x00004000)
static constexpr uint32_t kHeapBase      = 0x800401A8u;   // heap start == end of .bss
static constexpr uint32_t kHeapSizePtr   = 0x80030FB8u;   // __heapsize  (crt0 writes 0x001BBE50)
static constexpr uint32_t kHeapBasePtr   = 0x80030FB4u;   // __heapbase  (crt0 writes 0x800401A8)
static constexpr uint32_t kGp            = 0x80033674u;   // crt0's lui/addiu pair
static constexpr uint32_t kLibcInit      = 0x80026864u;   // BIOS A0:0x39 InitHeap thunk
static constexpr uint32_t kGameMain      = 0x80042C38u;   // vs_main_exec — crt0's second and last call
static constexpr uint32_t kCrt0          = kPsExeEntry;   // __SN_ENTRY_POINT

// static: a constexpr free function is implicitly inline, i.e. external linkage, and `in_text` is a
// name another TU could plausibly define differently — internal linkage keeps that an ODR non-event.
static constexpr bool in_text(uint32_t a) {
  return a >= kPsExeTextAddr && a < kPsExeTextAddr + kPsExeTextSize;
}
// Every relation below is one the measurement established. If a later edit "corrects" a field from a
// reference — the exact temptation this repo has, with a matching decomp sitting in external/ — the
// build fails and names the relation, instead of the port booting into a subtly wrong crt0.
static_assert(in_text(kBssZeroLo) && in_text(kBssZeroHi) && in_text(kStackTopBase) &&
              in_text(kStackTopBase2) && in_text(kHeapBase) && in_text(kHeapSizePtr) &&
              in_text(kHeapBasePtr) && in_text(kGp) && in_text(kLibcInit) && in_text(kGameMain) &&
              in_text(kCrt0),
              "every boot-group address must lie inside the ONE loaded image — this game has no "
              "separate .data/.bss segment (header d_size = b_size = 0), so an address outside "
              "[t_addr, t_addr+t_size) cannot be one crt0 touched");
static_assert(kBssZeroLo < kBssZeroHi, "bssZeroLo must precede bssZeroHi");
static_assert(kBssZeroHi - kBssZeroLo == 52016u,
              "the measured .bss clear is 52,016 bytes / 13,004 words; a changed size means the loop "
              "bounds were re-derived, and tools/re_crt0.py must be re-run to say from what");
static_assert(kHeapBase == kBssZeroHi,
              "crt0 materialises 0x800401A8 TWICE with the same immediate — 0x8001F54C/50 into $v1 as "
              "the clear loop's bound, 0x8001F580/84 into $a0 as the heap base — so the two constants "
              "are the same measured number and disagreeing would mean one was hand-edited. NOTE the "
              "relation is all this asserts: it does NOT mean the heap is free RAM. 0x800401A8 is the "
              "end of the FIRST of three linked segments' .bss, and the arena crt0 declares runs "
              "through 138,836 bytes of the loaded image above it — note 3 in the block above");
static_assert(kStackTopBase2 == kStackTopBase + 4u,
              "_stacksize sits immediately after _ramsize; crt0 reads them as an adjacent pair");
static_assert(kGp == kBssZeroLo - 4u,
              "gp is one word below the .bss start (crt0's lui/addiu pair). This is an internal "
              "relation, NOT independent confirmation: this executable contains ZERO gp-relative "
              "load/stores in code (measured — 4 candidate encodings in the whole image, all 4 inside "
              "byte-ramp DATA tables), so nothing but that instruction pair can confirm gp");

// DESIGNATED initialisers, deliberately. GameConfig is initialised POSITIONALLY by the older
// consumers in this workspace, and the framework appends fields to it — which means a positional list
// silently re-binds every value after an inserted field. Binding by name makes an upstream insert a
// no-op here and an upstream RENAME a compile error naming the field, which is the signal we want.
// C++20 requires designators in declaration order; keep them so when adding one.
static const GameConfig g_vagrant_cfg = {
    // --- crt0 / boot -------------------------------------- RE-01, MEASURED (see the block above) --
    .bssZeroLo = kBssZeroLo, .bssZeroHi = kBssZeroHi,
    .stackTopBase = kStackTopBase, .stackTopBase2 = kStackTopBase2,
    .heapBase = kHeapBase,
    .heapSizePtr = kHeapSizePtr, .heapBasePtr = kHeapBasePtr,
    .gp = kGp,
    .libcInit = kLibcInit,
    .gameMain = kGameMain, .crt0 = kCrt0,

    // --- recompiled MAIN .text range (physical) ---------------------------------- RE-02, NOT DONE --
    // These come from the RECOMPILER's own generated/overlay_table.h (REC_MAIN_LO / REC_MAIN_HI) so
    // they can never drift from the substrate they describe. There is no substrate yet, so they are
    // zero and this file does not #include that header — including a generated header that does not
    // exist would make the tree un-configurable rather than honestly incomplete.
    .recMainLo = 0, .recMainHi = 0,

    // --- disc key ----------------------------------------------- this port's own env name, not RE --
    // Not an RE fact but a port fact, and it belongs here because the framework must not know it: the
    // resolver used to hardcode the FIRST consumer's variable, so a second port set its own key,
    // nothing read it, and every boot ran with NO MEDIA behind an ordinary-looking log.
    // tools/resolve_disc.py implements the same key on the host side.
    .discEnvVar = "PSXPORT_VAGRANT_DISC",

    // --- boot intro movies ------------------------------------------- deliberately EMPTY, and why --
    // Not a gap. The framework's native .STR player only plays what a port ASKS it to play, and this
    // port asks for nothing: there is no native boot here yet, so any movie is the GUEST's to play on
    // the substrate. The disc does carry MOV/*.STR files; naming one here without knowing which the
    // boot plays would be a guess wearing a citation.
    .bootFmv = { nullptr, nullptr, nullptr, nullptr },

    // --- per-frame OT / packet pool ---------------------------------------------- RE-05, NOT DONE --
    .otRegionBase = 0, .otRegionStride = 0,
    .packetPoolBase = 0, .packetPoolStride = 0,
    .otBasePtr = 0,
    .dwellCounter = 0,
    .poolPtrCur = 0, .poolPtrLast = 0,
    .clearOtagR = 0, .putDrawEnv = 0, .drawSync = 0,
    .irqEventClasses = {0, 0, 0},
    .dualviewRenderOrch = 0, .dualviewSubmit = 0,

    // --- scheduler task layout ------------------------------- N/A until a native frame loop exists --
    // The framework's PcScheduler is not wired for this port: GameHooks' scheduler entries are
    // fail-fast stubs, so these values would have no reader even if they were known.
    .taskTableBase = 0, .taskSlotStride = 0, .taskCount = 0,
    .curTaskPtr = 0,
    .stageStart = 0, .stageDemo = 0, .stageGame = 0,

    // --- overlay router slots --------------------------------------------------- RE-03, MEASURED --
    // This game HAS overlay modules — 21 .PRG files on the disc (BATTLE, TITLE, ENDING, INITBTL,
    // SCREFF2 and 16 MENU/*), one of which (MENUA.PRG) is 0 bytes and has no code/base. For every
    // non-empty image, tools/re_overlay.py M2 derives the base from that image's own absolute `jal`
    // targets and function-entry offsets; M3 SHA-binds OUR bytes to rood-reverse and independently
    // checks its link address. All 20 agree, and the executable contains all three slot values in
    // four contiguous resident words at 0x80010000..0x8001000C. The callbacks remain null because
    // no overlay substrate exists yet; RE-02, not RE-03, owns generating/registering code.
    .overlaySlots = { {0x80068800, nullptr}, {0x800F9800, nullptr}, {0x80102800, nullptr} },

    // --- CD chokepoints ---------------------------------------------------------- RE-04, NOT DONE --
    .cdInit = 0, .cdCommand = 0, .cdSync = 0, .cdReadPrim = 0, .cdFileLoad = 0, .cdAsyncRead = 0,
    .voicePlay = 0, .voiceStop = 0, .lastSectorTracker = 0,
    .cdInlineLoad = 0,
    .cdCmdStream = 0,
    .cdCallbackTable = {0, 0, 0, 0},
    .cdCallbackFn = {0, 0, 0, 0},
    .cdGetSector = 0,
    .cdReadyCbPtr = 0,
    .cdLastPosBuf = 0,
    .cdReadStock = 0, .cdReadSync = 0,
    .cdSearchFile = 0,
    .dmaCallbackTable = 0,

    // --- pad driver -------------------------------------------------------------- RE-06, NOT DONE --
    .padSlot0Buf = 0, .padSlot1Buf = 0, .padDriverFn = 0,
    .padSlotPtrTable = 0,
    .padSlotPtrStride = 0,

    // --- platform HLE (the hardware-sync primitives) ----------------------------- RE-08, NOT DONE --
    // Retagged from RE-01 to RE-08 on 2026-08-12: RE-01 is the crt0 GROUP consumed by crt0_setup
    // (the fields above) and it is now MEASURED, so leaving these windows under the same step number
    // would have made a done RE-01 imply a done HLE. They are a separate step and RE-08 is it.
    // ZERO MEANS "not RE'd, install nothing". initBuiltins() then registers no handler and says so;
    // a run that needs one hangs in the guest's real spin loop, which is the honest signal that the RE
    // is outstanding. The windows are zero too, so register_() refuses everything — this game has not
    // stated its memory map yet, and a window guessed from another game's map is how a handler lands
    // on an unrelated function.
    .hle = {},

    // --- rendering policy ------------------------------------------------- 1 while the guest draws --
    // The renderer clears to black on the principle "show ONLY what a native producer submitted".
    // That is right for a port whose native renderer owns the frame and WRONG for one still running
    // the guest's drawing code, where an upload into the display area IS visible on real hardware:
    // logo screens, FMV stills and menus that are uploads with no primitives render black. This port
    // owns no drawing at all, so the guest's uploads must survive.
    .preserveVramBackdrop = 1,

    // --- memory card ------------------------------------------------------ this port's own key/path --
    .cardEnvVar = "PSXPORT_VAGRANT_CARD",
    .cardDefaultPath = "scratch/saves/vagrant.mcr",

    // --- frame pacing ------------------------------------------------ 1 field per pacing call, and why --
    // The framework REQUIRES this field ("a new game MUST set this field"): zero used to fall through
    // to reading the first consumer's engine byte out of the scratchpad, which in any other game is
    // ordinary working memory, so a second consumer slept on garbage. The semantics are by CALLING
    // CADENCE, not by the game's display rate — a port that still runs the guest's own frame loop and
    // paces once per FIELD sets 1, which is this port's shape (there is no native loop here). Revisit
    // together with RE-05 if a native loop ever calls the pacer once per logic frame.
    .paceQuota = 1,

    .windowTitle = "Vagrant Story (psxport)",
    // crt0 stack-top bias, MEASURED by psxport tools/crt0_extract over this game's own boot
    // executable (SLUS_010.40, entry 0x8001F544). `declared = 1` is mandatory: crt0_plan REFUSES a boot when it is 0,
    // because 0 is a REAL measured answer for some crt0s and so cannot double as "unset".
    .stackBias = {1, -8},
};

// THE a1 CONTRACT, and why this file records it rather than doing anything about it. libcInit here
// (0x80026864) is a BIOS A0:0x39 InitHeap thunk, and psxport's HLE implements it as `heapInit(a0, a1)`
// — so the arena's SIZE is whatever `a1` holds at the call. The guest crt0 provably passes it
// (0x8001F5A0 `subu $a1,$a1,$a0`, a1 = 0x001BBE50 live into the jal at 0x8001F5CC, note 4 above).
//
// The framework used to set only `r[4]`, creating every arena with size 0. FIXED upstream in psxport
// 726d10c9 — which this repo pins — where the boot group became a pure `crt0_plan` in
// runtime/recomp/crt0_boot.h and `crt0_apply` sets both argument registers. Deleting the a1 store
// turns psxport's tests/test_crt0_boot_group.cpp red, so it cannot silently regress.
//
// TWO THINGS MEASURING THIS TAUGHT US, both worth more than the one-line fix (docs/issues/0003):
//   * It was NEVER Vagrant-specific. Tomba! 2, Spyro and Spider-Man each log "a1 held 0x00000000
//     before crt0 set it" on a real boot — the framework's own reference consumer was building a
//     zero-capacity heap too. An earlier version of this note predicted Tomba! 2 would be immune
//     because its libcInit was "likely a linked libc routine"; crt0_extract measures it as a BIOS
//     thunk, so that inference was wrong.
//   * It is INERT for THIS game, and the argument is structural rather than hopeful: SLUS_010.40
//     contains no malloc/free/calloc/realloc A0 thunk at all, and InitHeap's only caller is crt0
//     (re_crt0.py, 2,023 jal sites against 19 A0 thunks). The game uses its own allocator
//     (`vs_main_initHeap` 0x80043F74). So this port can demonstrate neither the bug nor the fix, and
//     a green boot here says nothing about either.

const GameConfig* vagrant_game_config() { return &g_vagrant_cfg; }

// Installs BOTH halves of the seam, because a Core's ctor snapshots them together — installing a
// config without its hooks leaves a Core holding a half-seam.
void vagrant_install_game_config() {
  extern const GameHooks* vagrant_game_hooks();   // game/core/game_hooks.cpp
  psxport_install_game(&g_vagrant_cfg, vagrant_game_hooks());
}
