#!/usr/bin/env python3
"""re_crt0.py — MEASURE the crt0 boot group of SLUS_010.40 out of the executable's own bytes.

  python3 tools/re_crt0.py [path/to/SLUS_010.40]     # measure, print each field + its citation
  python3 tools/re_crt0.py --selftest                # gate BOTH classes (positive AND negative)
  python3 tools/re_crt0.py --check-config            # SHIPPED constants vs MEASURED ones (the gate)
  python3 tools/re_crt0.py --gate-citations           # the .cpp's disassembly block vs the bytes
  python3 tools/re_crt0.py --emit-citations           # regenerate that block from the bytes
  python3 tools/re_crt0.py --gate-config             # do game_config.cpp's static_asserts FIRE?
  python3 tools/re_crt0.py --disasm 0x8001F544 40    # raw disassembly of a vaddr range (audit aid)

This is the instrument behind RE-01 (docs/re-frontier.md): it produces the eleven `GameConfig` boot
fields the framework's `crt0_setup` consumes (bssZeroLo/Hi, stackTopBase/2, heapBase,
heapSizePtr/heapBasePtr, gp, libcInit, gameMain, crt0).

HOW, and why this shape rather than a pattern match: it EXECUTES the crt0, starting at the PS-EXE
header's own entry PC, on a tiny concrete MIPS interpreter over the executable image, and reports what
that execution actually did — every store it made, every load it made, the two calls it made. Nothing
is keyed to an address this file knows in advance, so the numbers cannot be a transcription of a
reference: change the executable and the output changes with it. The `.bss` range is the store loop's
own footprint, not a symbol lookup.

WHAT A NEGATIVE PRINTS, designed before the positive (the standing rule: a diagnostic that can print
nothing is lying). This tool never reports a partial boot group and never substitutes a default:

  * no executable / not a PS-EXE            -> exit 2, naming the path it looked at
  * an opcode the interpreter does not know -> exit 2, naming pc + the raw word (it refuses to guess
                                              what an unmodelled instruction did to the registers)
  * fewer than 2 calls / 2 loads / no store loop, or a field that stayed unknown
                                           -> exit 2, printing the FULL execution log (every store,
                                              load and call it did see) plus the list of fields it
                                              could not establish
  * a value that fails a structural check (range ordering, targets inside the loaded image)
                                           -> exit 2, naming the check and both operands

so "it printed nothing" is not reachable: either eleven fields with citations, or a non-zero exit
saying what it saw instead. Exit codes: 0 = measured, 2 = refused (see above), 1 = selftest FAILED.

RELATIONSHIP TO psxport's `tools/crt0_extract` — KEEP BOTH, and do not write a third. As of
2026-08-12 the framework has its own crt0 reader, and it is NOT a duplicate of this one:

  * `crt0_extract` does SYMBOLIC straight-line decoding (35 instructions) and exists to be the SAME
    code as the boot-time gate: it calls `crt0_scan` out of psxport's `runtime/recomp/crt0_verify.h`,
    which is what `crt0_audit` runs on every boot of every port. Its job is that the extractor and
    the gate cannot drift, across all six games.
  * THIS tool CONCRETELY INTERPRETS the crt0 (52,051 instructions from the header entry PC) and
    reports what execution actually did, with a per-field disassembly citation, an independent
    witness from the SN link record, a heap-arena overlap analysis and a BIOS-thunk census. It is
    the RE instrument; it sees things a straight-line scan cannot.

They were cross-validated on these bytes and agree on all 8 shared fields with ZERO disagreements
(claim C005). That agreement is the reason to keep both: two methods sharing no code are a real
check on each other, and collapsing them into one would delete the check. If they ever disagree,
NEITHER is automatically right — read C005's falsifier first.

THIS TOOL KEEPS NO SECOND COPY OF THE ANSWER, and that is the point of `--check-config`. It used to
hold a `FIXTURE_EXPECT` table of the eleven values and assert the binary still matched *it*, while
game/core/game_config.cpp held a SECOND hand-typed copy in its `kXxx` constants and nothing compared
the two. Both gates passed with `kHeapSizePtr` moved +4 and `kLibcInit` pointed at an unrelated nop —
the shipped value was unchecked (workspace PROTOCOL.md, "THE SHIPPED VALUE MUST BE COMPARED TO THE
MEASURED ONE"). Now the SHIPPING FILE IS THE FIXTURE: `--check-config` parses game_config.cpp's eleven
constants AND the designated initialisers that bind them to GameConfig fields, and diffs them against
what this tool measures from the bytes. One comparison; a hand-edit of either side goes red.

The 22-line disassembly block in that file was the same defect one level down: it was RETYPED, not
pasted (three of its raw words did not match the executable — `8001F548` read `24427836` for a real
`24423678`), and nothing checked it, so the audit trail CLAUDE.md rule 1 demands was fiction. It is now
GENERATED (`--emit-citations`) and gated (`--gate-citations` regenerates it and requires byte-equality
with the block in the file), so a retyped word cannot survive.

NOT IN SCOPE, deliberately: this says nothing about the 21 .PRG overlay modules (RE-03), whose load
bases are not in this executable's header and must be observed on the loader.
"""
import hashlib
import os
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_EXE = os.path.join(ROOT, "scratch", "bin", "vagrant", "SLUS_010.40")
CONFIG_SRC = os.path.join(ROOT, "game", "core", "game_config.cpp")

# The image this tool's expectations were measured against (2026-08-12). The positive class is only
# meaningful pinned to a known image: a different SLUS_010.40 must FAIL rather than silently redefine
# the answer.
#
# There is deliberately NO table of expected field values here. game/core/game_config.cpp holds the
# ONE recorded copy and --check-config diffs it against the measurement; see the module docstring.
FIXTURE_SHA1 = "fababcfd4325d42f350d95b3472874affeb0e48c"

# The SN linker's own record of the FIRST linked segment, which SNMAIN.c keeps as file-scope statics
# and which therefore sits at a fixed address in this image. It is an INDEPENDENT witness for two of
# the measured values (bssZeroHi and gp) because it is link-time metadata, not the crt0 instruction
# stream: __bss + __bsslen == bssZeroHi, and __data + __datalen == gp.
SN_LINK_RECORD = 0x80030FBC        # __text, __textlen, __data, __datalen, __bss, __bsslen

RA_SENTINEL = 0xDEADBE00      # a value crt0's `sw $ra` cannot be confused with a real address
MAX_STEPS = 200000            # the .bss loop is ~13k iterations; anything past this is not this crt0


class Refuse(Exception):
    """Raised for every 'I cannot establish this' path. Carries the text the user must see."""


# ─────────────────────────────────────────────────────────────────────── the image ────────────────
class Image:
    """A loaded PS-EXE: header + a flat vaddr->byte mapping over the single loaded text image."""

    def __init__(self, path):
        self.path = path
        if not os.path.isfile(path):
            raise Refuse(f"no executable at {path}\n"
                         f"  Nothing was scanned. Extract it from YOUR disc first:\n"
                         f"    python3 tools/extract_exe.py\n"
                         f"  (scratch/ is gitignored; the executable is the copyright holder's)")
        self.data = open(path, "rb").read()
        if self.data[:8] != b"PS-X EXE":
            raise Refuse(f"{path} is {len(self.data)} bytes but does not start with 'PS-X EXE' "
                         f"(first 8 bytes: {self.data[:8]!r}) — this is not a PS1 executable, and "
                         f"nothing was measured")
        f = struct.unpack("<11I", self.data[0x10:0x10 + 44])
        (self.pc0, self.gp0, self.t_addr, self.t_size, self.d_addr, self.d_size,
         self.b_addr, self.b_size, self.s_addr, self.s_size, self.sp_gp) = f
        self.lo, self.hi = self.t_addr, self.t_addr + self.t_size
        self.delta = self.t_addr - 0x800          # vaddr = file_off + delta
        if len(self.data) < 0x800 + self.t_size:
            raise Refuse(f"{path}: header says t_size=0x{self.t_size:X} but the file holds only "
                         f"0x{len(self.data) - 0x800:X} bytes of text — truncated image, nothing measured")
        if not (self.lo <= self.pc0 < self.hi):
            raise Refuse(f"{path}: header entry pc0=0x{self.pc0:08X} is OUTSIDE the loaded text "
                         f"[0x{self.lo:08X},0x{self.hi:08X}) — the header is unreadable, nothing measured")

    def sha1(self):
        return hashlib.sha1(self.data).hexdigest()

    def inside(self, va):
        return self.lo <= (va & 0xFFFFFFFF) < self.hi

    def off(self, va):
        return (va & 0xFFFFFFFF) - self.delta

    def r32(self, va):
        o = self.off(va)
        if not (0 <= o <= len(self.data) - 4):
            raise Refuse(f"crt0 read 0x{va:08X}, which is not inside the loaded image "
                         f"[0x{self.lo:08X},0x{self.hi:08X}) — refusing to invent its contents")
        return struct.unpack("<I", self.data[o:o + 4])[0]

    def word_at(self, va):
        return self.r32(va)


# ────────────────────────────────────────────────────────────── the tiny interpreter ──────────────
REG = ["zero", "at", "v0", "v1", "a0", "a1", "a2", "a3", "t0", "t1", "t2", "t3", "t4", "t5", "t6",
       "t7", "s0", "s1", "s2", "s3", "s4", "s5", "s6", "s7", "t8", "t9", "k0", "k1", "gp", "sp",
       "fp", "ra"]


def s16(v):
    return v - 0x10000 if v & 0x8000 else v


def disasm1(w, pc):
    """One-line disassembly, good enough to be the CITATION printed next to each measured field."""
    op, rs, rt, rd, sa, fn = w >> 26, (w >> 21) & 31, (w >> 16) & 31, (w >> 11) & 31, (w >> 6) & 31, w & 63
    im, tgt = w & 0xFFFF, (pc + 4 & 0xF0000000) | ((w & 0x3FFFFFF) << 2)
    R = lambda i: "$" + REG[i]
    if w == 0:
        return "nop"
    if op == 0x00:
        return {0x00: f"sll {R(rd)}, {R(rt)}, {sa}", 0x02: f"srl {R(rd)}, {R(rt)}, {sa}",
                0x03: f"sra {R(rd)}, {R(rt)}, {sa}", 0x08: f"jr {R(rs)}",
                0x09: f"jalr {R(rd)}, {R(rs)}", 0x0D: "break",
                0x21: f"addu {R(rd)}, {R(rs)}, {R(rt)}", 0x23: f"subu {R(rd)}, {R(rs)}, {R(rt)}",
                0x24: f"and {R(rd)}, {R(rs)}, {R(rt)}", 0x25: f"or {R(rd)}, {R(rs)}, {R(rt)}",
                0x2A: f"slt {R(rd)}, {R(rs)}, {R(rt)}", 0x2B: f"sltu {R(rd)}, {R(rs)}, {R(rt)}",
                }.get(fn, f".word 0x{w:08X}")
    return {0x02: f"j 0x{tgt:08X}", 0x03: f"jal 0x{tgt:08X}",
            0x04: f"beq {R(rs)}, {R(rt)}, 0x{pc + 4 + 4 * s16(im):08X}",
            0x05: f"bne {R(rs)}, {R(rt)}, 0x{pc + 4 + 4 * s16(im):08X}",
            0x08: f"addi {R(rt)}, {R(rs)}, {s16(im):#x}", 0x09: f"addiu {R(rt)}, {R(rs)}, {s16(im):#x}",
            0x0A: f"slti {R(rt)}, {R(rs)}, {s16(im):#x}", 0x0B: f"sltiu {R(rt)}, {R(rs)}, {s16(im):#x}",
            0x0C: f"andi {R(rt)}, {R(rs)}, {im:#x}", 0x0D: f"ori {R(rt)}, {R(rs)}, {im:#x}",
            0x0F: f"lui {R(rt)}, {im:#x}", 0x23: f"lw {R(rt)}, {s16(im):#x}({R(rs)})",
            0x2B: f"sw {R(rt)}, {s16(im):#x}({R(rs)})",
            }.get(op, f".word 0x{w:08X}")


class Trace:
    def __init__(self):
        self.stores = []   # (pc, addr, value)
        self.loads = []    # (pc, addr, value)
        self.calls = []    # (pc, target, a0, a1, gp)
        self.steps = 0


def run_crt0(img, entry=None):
    """Execute crt0 from the header's entry PC until its SECOND call. Returns (Trace, regs)."""
    pc = img.pc0 if entry is None else entry
    r = [0] * 32
    r[31] = RA_SENTINEL
    mem = {}                      # crt0's own writes, so a later read sees them (none needed today)
    tr = Trace()

    def load(va):
        return mem.get(va & 0xFFFFFFFC, None) if (va & 0xFFFFFFFC) in mem else img.r32(va)

    def step(pc, in_delay):
        """Execute the instruction at pc. Returns (next_pc, branch_target_or_None)."""
        w = img.word_at(pc)
        op, rs, rt, rd, sa, fn = w >> 26, (w >> 21) & 31, (w >> 16) & 31, (w >> 11) & 31, (w >> 6) & 31, w & 63
        im = w & 0xFFFF
        M = 0xFFFFFFFF
        nxt, brt = pc + 4, None
        if w == 0:
            pass
        elif op == 0x00:
            if fn == 0x00:
                r[rd] = (r[rt] << sa) & M
            elif fn == 0x02:
                r[rd] = (r[rt] & M) >> sa
            elif fn == 0x03:
                r[rd] = (((r[rt] & M) - (1 << 32) if r[rt] & 0x80000000 else r[rt]) >> sa) & M
            elif fn == 0x21:
                r[rd] = (r[rs] + r[rt]) & M
            elif fn == 0x23:
                r[rd] = (r[rs] - r[rt]) & M
            elif fn == 0x24:
                r[rd] = r[rs] & r[rt]
            elif fn == 0x25:
                r[rd] = r[rs] | r[rt]
            elif fn == 0x2A:
                a = r[rs] - (1 << 32) if r[rs] & 0x80000000 else r[rs]
                b = r[rt] - (1 << 32) if r[rt] & 0x80000000 else r[rt]
                r[rd] = 1 if a < b else 0
            elif fn == 0x2B:
                r[rd] = 1 if (r[rs] & M) < (r[rt] & M) else 0
            elif fn == 0x0D:
                raise Refuse(f"crt0 hit `break` at 0x{pc:08X} before making two calls — this is not "
                             f"the SN crt0 shape the boot group is defined by")
            elif fn == 0x08:
                raise Refuse(f"crt0 returned (`jr {REG[rs]}`) at 0x{pc:08X} before making two calls — "
                             f"the entry point is not a crt0")
            else:
                raise Refuse(f"UNMODELLED instruction at 0x{pc:08X}: 0x{w:08X} ({disasm1(w, pc)})\n"
                             f"  Refusing to continue: an unmodelled instruction means every register "
                             f"value after it is unknown, and a boot group derived from unknown "
                             f"registers would be a guess wearing a measurement's clothes.")
        elif op == 0x0F:
            r[rt] = (im << 16) & M
        elif op in (0x08, 0x09):
            r[rt] = (r[rs] + s16(im)) & M
        elif op == 0x0C:
            r[rt] = r[rs] & im
        elif op == 0x0D:
            r[rt] = r[rs] | im
        elif op in (0x0A, 0x0B):
            a = r[rs] - (1 << 32) if (op == 0x0A and r[rs] & 0x80000000) else r[rs]
            r[rt] = 1 if a < (s16(im) if op == 0x0A else im) else 0
        elif op == 0x23:
            va = (r[rs] + s16(im)) & M
            v = load(va)
            r[rt] = v
            tr.loads.append((pc, va, v))
        elif op == 0x2B:
            va = (r[rs] + s16(im)) & M
            mem[va & 0xFFFFFFFC] = r[rt]
            tr.stores.append((pc, va, r[rt]))
        elif op in (0x04, 0x05):
            taken = (r[rs] == r[rt]) if op == 0x04 else (r[rs] != r[rt])
            if taken:
                brt = (pc + 4 + 4 * s16(im)) & M
        elif op == 0x02:
            brt = ((pc + 4) & 0xF0000000) | ((w & 0x3FFFFFF) << 2)
        elif op == 0x03:
            brt = ((pc + 4) & 0xF0000000) | ((w & 0x3FFFFFF) << 2)
            r[31] = pc + 8
        else:
            raise Refuse(f"UNMODELLED instruction at 0x{pc:08X}: 0x{w:08X} ({disasm1(w, pc)})\n"
                         f"  Refusing to continue (see above): unknown registers cannot produce a "
                         f"measured boot group.")
        if in_delay and brt is not None:
            raise Refuse(f"branch in a delay slot at 0x{pc:08X} — the interpreter will not model this")
        return nxt, brt, (op == 0x03), brt

    while True:
        tr.steps += 1
        if tr.steps > MAX_STEPS:
            raise Refuse(f"crt0 ran {MAX_STEPS} instructions without reaching its second call "
                         f"(stores seen: {len(tr.stores)}, loads: {len(tr.loads)}, "
                         f"calls: {len(tr.calls)}) — refusing to report a boot group from a run that "
                         f"did not terminate the way the SN crt0 does")
        nxt, brt, is_call, target = step(pc, False)
        if brt is None:
            pc = nxt
            continue
        # delay slot executes before the transfer (crt0 puts `addi $a0,$a0,4` in the jal's slot)
        step(nxt, True)
        if is_call:
            tr.calls.append((pc, target, r[4], r[5], r[28]))
            if len(tr.calls) >= 2:
                return tr, r
            pc = nxt + 4         # a call RETURNS; do not follow it (its body is not crt0)
        else:
            pc = brt
    # unreachable


# ──────────────────────────────────────────────────────── the boot group, from the trace ──────────
def measure(img):
    """Turn the crt0 execution trace into the eleven GameConfig boot fields, or refuse."""
    tr, r = run_crt0(img)
    out, cite = {}, {}

    def note(k, v, pc, extra=""):
        out[k] = v
        w = img.word_at(pc)
        cite[k] = f"0x{pc:08X}  {w:08x}  {disasm1(w, pc)}" + (f"   [{extra}]" if extra else "")

    out["crt0"] = img.pc0
    cite["crt0"] = f"PS-EXE header pc0 (file offset 0x10) = 0x{img.pc0:08X}"

    # --- the .bss clear: the LONGEST run of consecutive 4-byte stores of zero -------------------
    zeros = sorted({a for _, a, v in tr.stores if v == 0})
    best, run = (None, None), []
    for a in zeros:
        if run and a == run[-1] + 4:
            run.append(a)
        else:
            run = [a]
        if best[0] is None or (run[-1] - run[0]) > (best[1] - best[0]):
            best = (run[0], run[-1])
    if best[0] is None or best[1] - best[0] < 0x100:
        raise Refuse("no .bss clear loop found in crt0 — the longest consecutive run of zero stores "
                     f"was {0 if best[0] is None else best[1] - best[0] + 4} bytes.\n"
                     f"  Execution log: {len(tr.stores)} stores, {len(tr.loads)} loads, "
                     f"{len(tr.calls)} calls over {tr.steps} instructions.\n" + logdump(img, tr))
    zpc = next(pc for pc, a, v in tr.stores if a == best[0] and v == 0)
    note("bssZeroLo", best[0], zpc, "first word the clear loop stored 0 to")
    note("bssZeroHi", best[1] + 4, zpc, f"last stored word 0x{best[1]:08X} + 4 (exclusive end)")

    # --- the two loads crt0 makes are the stack-top globals, in order ---------------------------
    if len(tr.loads) < 2:
        raise Refuse(f"crt0 made {len(tr.loads)} loads; the boot group needs the two stack-top "
                     f"globals.\n" + logdump(img, tr))
    note("stackTopBase", tr.loads[0][1], tr.loads[0][0], f"loaded 0x{tr.loads[0][2]:08X}")
    note("stackTopBase2", tr.loads[1][1], tr.loads[1][0], f"loaded 0x{tr.loads[1][2]:08X}")

    # --- the heap globals: the two stores of a NON-zero value outside the clear range -----------
    heapish = [(pc, a, v) for pc, a, v in tr.stores
               if not (best[0] <= a <= best[1]) and v != 0 and v != RA_SENTINEL]
    if len(heapish) != 2:
        raise Refuse(f"expected exactly 2 heap globals written by crt0 (size and base); found "
                     f"{len(heapish)}: " + ", ".join(f"[0x{a:08X}]=0x{v:08X}" for _, a, v in heapish)
                     + "\n" + logdump(img, tr))
    # The BASE is the one whose stored value is a KSEG0 pointer inside RAM; the other is the size.
    based = [t for t in heapish if 0x80000000 <= t[2] < 0x80200000]
    sized = [t for t in heapish if t not in based]
    if len(based) != 1 or len(sized) != 1:
        raise Refuse("could not tell the heap BASE store from the heap SIZE store: "
                     + ", ".join(f"[0x{a:08X}]=0x{v:08X}" for _, a, v in heapish) + "\n"
                     + logdump(img, tr))
    note("heapBasePtr", based[0][1], based[0][0], f"stored 0x{based[0][2]:08X}")
    note("heapSizePtr", sized[0][1], sized[0][0], f"stored 0x{sized[0][2]:08X}")
    out["heapBase"] = based[0][2]
    cite["heapBase"] = cite["heapBasePtr"] + "  (the VALUE crt0 wrote as the heap base)"

    # --- gp / the two calls ---------------------------------------------------------------------
    cpc, ctgt, ca0, ca1, cgp = tr.calls[0]
    out["gp"] = cgp
    cite["gp"] = f"$gp at the first call = 0x{cgp:08X} (set by the lui/addiu pair above 0x{cpc:08X})"
    note("libcInit", ctgt, cpc, f"a0=0x{ca0:08X} a1=0x{ca1:08X}")
    note("gameMain", tr.calls[1][1], tr.calls[1][0], "the second and last call crt0 makes")

    # --- structural checks: each one names both operands when it fires --------------------------
    def chk(cond, msg):
        if not cond:
            raise Refuse("STRUCTURAL CHECK FAILED: " + msg + "\n" + logdump(img, tr))

    chk(out["bssZeroLo"] < out["bssZeroHi"],
        f"bss range is not ordered: lo=0x{out['bssZeroLo']:08X} hi=0x{out['bssZeroHi']:08X}")
    for k in ("bssZeroLo", "bssZeroHi", "stackTopBase", "stackTopBase2", "heapSizePtr",
              "heapBasePtr", "gp", "libcInit", "gameMain", "crt0"):
        chk(img.inside(out[k]) or k == "heapBase",
            f"{k}=0x{out[k]:08X} is outside the loaded image "
            f"[0x{img.lo:08X},0x{img.hi:08X}) — a boot-group address must be a real address in this "
            f"executable")
    chk(out["heapBase"] == out["bssZeroHi"],
        f"heapBase=0x{out['heapBase']:08X} != bssZeroHi=0x{out['bssZeroHi']:08X}; in the SN crt0 the "
        f"heap starts where .bss ends. Not fatal in principle — but it means one of the two was "
        f"misidentified, so this tool refuses rather than ship a half-right group")
    # a1 at the libc-init call: the BIOS InitHeap(addr,size) contract needs it, so report it loudly
    out["_initHeapA0"], out["_initHeapA1"] = ca0, ca1
    out["_sp"] = r[29]

    # --- the SN link record: an INDEPENDENT witness for bssZeroHi and gp -------------------------
    # Two of the eleven values are confirmable without looking at crt0's instructions at all, because
    # the SN startup object keeps the linker's segment table as initialised data in this image. If the
    # record is not there (a different link, a different game) this REFUSES rather than skipping the
    # cross-check silently — a cross-check that can no-op is not a cross-check.
    rec = [img.word_at(SN_LINK_RECORD + 4 * i) for i in range(6)]
    out["_snLink"] = rec
    text, textlen, data, datalen, bss, bsslen = rec
    chk(img.inside(text) and img.inside(data) and img.inside(bss),
        f"the SN link record at 0x{SN_LINK_RECORD:08X} does not hold three in-image addresses "
        f"(__text=0x{text:08X} __data=0x{data:08X} __bss=0x{bss:08X}) — this image does not carry the "
        f"record this cross-check reads, so bssZeroHi and gp would have NO independent witness")
    chk(text + textlen == data,
        f"SN link record: __text+__textlen = 0x{text + textlen:08X} != __data = 0x{data:08X}")
    chk(data + datalen == out["gp"],
        f"SN link record: __data+__datalen = 0x{data + datalen:08X} != measured gp = "
        f"0x{out['gp']:08X}. These are independent sources (link metadata vs crt0's lui/addiu pair); "
        f"a disagreement means one of them is not what this tool thinks it is")
    chk(bss + bsslen == out["bssZeroHi"],
        f"SN link record: __bss+__bsslen = 0x{bss + bsslen:08X} != measured bssZeroHi = "
        f"0x{out['bssZeroHi']:08X}. Independent sources; a disagreement is a real contradiction")

    # --- WHAT THE DECLARED HEAP ACTUALLY OVERLAPS ------------------------------------------------
    # This is the measurement that refuted "the heap starts where .bss ends, so the heap is free RAM".
    # crt0's heap base is the end of the FIRST linked segment's .bss; this executable concatenates
    # THREE separately-linked segments, so the arena crt0 declares runs straight through the two above
    # it. Reported unconditionally, in both directions, so a reader cannot mistake silence for safety.
    arena_lo, arena_sz = out["_initHeapA0"], out["_initHeapA1"]
    arena_hi = (arena_lo + arena_sz) & 0xFFFFFFFF
    ov_lo, ov_hi = max(arena_lo, img.lo), min(arena_hi, img.hi)
    out["_arena"] = (arena_lo, arena_hi)
    out["_arenaOverlap"] = (ov_lo, ov_hi) if ov_hi > ov_lo else None
    out["_arenaOverlapNonZero"] = (
        sum(1 for b in img.data[img.off(ov_lo):img.off(ov_hi)] if b) if ov_hi > ov_lo else 0)
    hi_nz = max((o for o in range(img.off(img.hi) - 1, -1, -1) if img.data[o]), default=None)
    out["_imageTopNonZero"] = None if hi_nz is None else hi_nz + img.delta

    # --- IS THE BIOS HEAP EVER ALLOCATED FROM? counted, not assumed ------------------------------
    # The BIOS entry points reachable from a PS-EXE are `addiu $t2,$zero,0xA0 / jr $t2 / addiu
    # $t1,$zero,<fn>` thunks. Census every thunk in the image, then every `jal` in the image, and
    # report the CALLER COUNT for each heap-related thunk. A zero here is meaningful precisely because
    # the same pass prints the denominator (thunks found, jal sites scanned) — see WHAT A NEGATIVE
    # PRINTS in the docstring.
    out["_biosHeap"] = bios_heap_census(img)
    return out, cite, tr


# BIOS A0-table functions that allocate from, or create, the libc heap.
HEAP_FNS = {0x33: "malloc", 0x34: "free", 0x37: "calloc", 0x38: "realloc", 0x39: "InitHeap"}


def bios_heap_census(img):
    """Every BIOS A0 thunk in the image, and how many `jal` sites in the image target each. Returns
    (thunks_total, jal_total, [(va, fn, name, [caller_pcs])]) covering the HEAP_FNS thunks only."""
    n = (img.hi - img.lo) // 4
    words = struct.unpack(f"<{n}I", img.data[img.off(img.lo):img.off(img.hi)])
    thunks, jals, jal_total = {}, {}, 0
    for i, w in enumerate(words):
        va = img.lo + 4 * i
        if w == 0x240A00A0 and i + 2 < n and words[i + 1] == 0x01400008 and (words[i + 2] >> 16) == 0x2409:
            thunks[va] = words[i + 2] & 0xFFFF
        if w >> 26 == 0x03:
            jal_total += 1
            jals.setdefault(((va + 4) & 0xF0000000) | ((w & 0x3FFFFFF) << 2), []).append(va)
    rows = [(va, fn, HEAP_FNS[fn], jals.get(va, []))
            for va, fn in sorted(thunks.items()) if fn in HEAP_FNS]
    return len(thunks), jal_total, rows


def logdump(img, tr):
    L = ["  --- FULL crt0 execution log (what the tool DID see) ---",
         f"  {tr.steps} instructions, {len(tr.stores)} stores, {len(tr.loads)} loads, "
         f"{len(tr.calls)} calls"]
    seen, shown = set(), 0
    for pc, a, v in tr.stores:           # cap the BORING case: one line per distinct store SITE
        if pc in seen:
            continue
        seen.add(pc)
        L.append(f"    store @0x{pc:08X}  [0x{a:08X}] = 0x{v:08X}   {disasm1(img.word_at(pc), pc)}")
        shown += 1
    L.append(f"    ({shown} distinct store sites; repeats of a site collapsed)")
    for pc, a, v in tr.loads:
        L.append(f"    load  @0x{pc:08X}  [0x{a:08X}] -> 0x{v:08X}  {disasm1(img.word_at(pc), pc)}")
    for pc, t, a0, a1, gp in tr.calls:
        L.append(f"    call  @0x{pc:08X}  -> 0x{t:08X}  a0=0x{a0:08X} a1=0x{a1:08X} gp=0x{gp:08X}")
    return "\n".join(L)


ORDER = ["bssZeroLo", "bssZeroHi", "stackTopBase", "stackTopBase2", "heapBase", "heapSizePtr",
         "heapBasePtr", "gp", "libcInit", "gameMain", "crt0"]


def report(img, out, cite, tr):
    print(f"[crt0] {img.path}")
    print(f"[crt0] sha1 {img.sha1()}   text 0x{img.t_addr:08X} + 0x{img.t_size:X}   "
          f"entry 0x{img.pc0:08X}")
    print(f"[crt0] header d_size=0x{img.d_size:X} b_addr=0x{img.b_addr:08X} b_size=0x{img.b_size:X} "
          f"-> the loader clears NO .bss; the crt0 loop below is the only source for the range")
    print(f"[crt0] executed {tr.steps} instructions from the header entry PC to crt0's second call")
    print()
    w = max(len(k) for k in ORDER)
    for k in ORDER:
        print(f"  .{k:<{w}} = 0x{out[k]:08X}   {cite[k]}")
    print()
    print(f"  derived: sp = fp = 0x{out['_sp']:08X}   "
          f"(mem[0x{out['stackTopBase']:08X}] - 8, KSEG0)")
    print(f"  derived: the libc-init call is made with a0=0x{out['_initHeapA0']:08X} "
          f"a1=0x{out['_initHeapA1']:08X}  <-- BOTH are part of the contract")
    print()
    tx, txl, da, dal, bs, bsl = out["_snLink"]
    print(f"  INDEPENDENT WITNESS — the SN link record at 0x{SN_LINK_RECORD:08X} (initialised data, "
          f"not crt0 code):")
    print(f"    __text 0x{tx:08X}+0x{txl:X} -> 0x{tx + txl:08X}    __data 0x{da:08X}+0x{dal:X} -> "
          f"0x{da + dal:08X} == gp")
    print(f"    __bss  0x{bs:08X}+0x{bsl:X} -> 0x{bs + bsl:08X} == bssZeroHi")
    print(f"    It describes 0x{tx:08X}..0x{bs + bsl:08X} ONLY, i.e. the FIRST linked segment. The "
          f"loaded image runs to 0x{img.hi:08X}.")
    print()
    alo, ahi = out["_arena"]
    ov = out["_arenaOverlap"]
    print(f"  THE HEAP ARENA crt0 DECLARES IS NOT FREE RAM: [0x{alo:08X},0x{ahi:08X})")
    if ov is None:
        print(f"    ... and it does NOT overlap the loaded image [0x{img.lo:08X},0x{img.hi:08X}). "
              f"That contradicts what was measured on 2026-08-12 — re-derive before trusting it.")
    else:
        print(f"    overlaps the loaded image over [0x{ov[0]:08X},0x{ov[1]:08X}) = "
              f"{ov[1] - ov[0]} bytes, of which {out['_arenaOverlapNonZero']} are NON-ZERO; the "
              f"highest non-zero byte in the image is 0x{out['_imageTopNonZero']:08X}.")
        print(f"    So bssZeroHi is the end of the FIRST segment's .bss, not the end of the image: "
              f"gameMain 0x{out['gameMain']:08X} and the _ramsize/_stacksize globals "
              f"0x{out['stackTopBase']:08X}/0x{out['stackTopBase2']:08X} all sit INSIDE this arena.")
    thunks, jal_total, rows = out["_biosHeap"]
    print(f"  ... and it is never allocated from. Census over the whole image: {thunks} BIOS A0 "
          f"thunks, {jal_total} jal sites scanned.")
    for va, fn, name, callers in rows:
        print(f"    A0:0x{fn:02X} {name:<8} thunk 0x{va:08X}   {len(callers)} caller(s)"
              + (": " + ", ".join(f"0x{c:08X}" for c in callers) if callers else ""))
    print(f"    thunks present for: {', '.join(n for _, _, n, _ in rows) or 'NONE of malloc/free/'
          'calloc/realloc/InitHeap'}  (an absent thunk cannot be called from this image at all)")


# ─────────────────────────────── the shipped file IS the fixture (PROTOCOL.md's rule) ────────────
CIT_BEGIN = "// >>> BEGIN GENERATED CITATIONS"
CIT_END = "// <<< END GENERATED CITATIONS"

# GameConfig field -> the named constant game_config.cpp is expected to define for it. The parser
# checks the DESIGNATED INITIALISER too, so `.gp = kLibcInit` is caught: a right-valued constant bound
# to the wrong field ships a wrong value just as effectively as a wrong literal.
K_OF = {f: "k" + f[0].upper() + f[1:] for f in ORDER}


def emit_citations(img, out, cite, tr):
    """Build the disassembly citation block from the BYTES. This is the only writer of that block."""
    end = tr.calls[1][0] + 8                     # the second jal, its delay slot, and the `break`
    ann = {}                                     # citation pc -> the constants measured there
    for f in ORDER:                              # gp and crt0 cite a register/header, not a pc
        if cite[f].startswith("0x"):
            ann.setdefault(int(cite[f][2:10], 16), []).append(K_OF[f])
    L = [CIT_BEGIN + " — generated from the executable by `python3 tools/re_crt0.py",
         "//     --emit-citations`, and gated by `--gate-citations`, which regenerates this block and",
         "//     FAILS unless it is byte-identical to what is below. DO NOT HAND-EDIT: the hand-typed",
         "//     predecessor had three raw words that did not match the bytes (0x8001F548 read",
         "//     `24427836` for a real `24423678`), and nothing checked it. The arrows name the",
         "//     constants the measurement attributed to each line — they are emitted, not typed.",
         f"//   sha1 {img.sha1()}   entry 0x{img.pc0:08X}   {(end - img.pc0) // 4 + 1} instructions"]
    for va in range(img.pc0, end + 1, 4):
        w = img.word_at(va)
        s = f"//   {va:08X}  {w:08x}  {disasm1(w, va)}"
        if va in ann:
            s += " " * max(1, 44 - len(s)) + "<- " + ", ".join(ann[va])
        L.append(s)
    L.append(CIT_END)
    return L


def gate_citations(img, out, cite, tr, text):
    """Regenerate the block and require the file's copy to be byte-identical. Returns a list of
    failure strings; the negative it must be able to print is a NAMED differing line, not silence."""
    want = emit_citations(img, out, cite, tr)
    lines = text.splitlines()
    try:
        b = next(i for i, l in enumerate(lines) if l.startswith(CIT_BEGIN))
        e = next(i for i, l in enumerate(lines) if l.startswith(CIT_END))
    except StopIteration:
        return [f"game_config.cpp has no generated-citation block ({CIT_BEGIN!r} .. {CIT_END!r}) — "
                f"NOTHING was compared. Run --emit-citations and paste the block in."]
    got = lines[b:e + 1]
    if got == want:
        return []
    fails = [f"the citation block in game_config.cpp is NOT what the bytes produce "
             f"({len(got)} lines in the file, {len(want)} generated):"]
    for i in range(max(len(got), len(want))):
        g, w = (got[i] if i < len(got) else "<missing>"), (want[i] if i < len(want) else "<extra>")
        if g != w:
            fails.append(f"    line {b + i + 1}:  file: {g.strip()}")
            fails.append(f"    {' ' * len(str(b + i + 1))}         bytes: {w.strip()}")
    return fails


def parse_config(text):
    """Extract game_config.cpp's constants AND the field->constant bindings. Refuses loudly rather
    than checking a subset: a parse that silently finds 9 of 11 would certify the other two."""
    import re
    consts, unresolved = {}, {}
    for m in re.finditer(r"^static constexpr uint32_t\s+(\w+)\s*=\s*([^;]+);", text, re.M):
        name, expr = m.group(1), m.group(2).strip()
        if re.fullmatch(r"0[xX][0-9a-fA-F]+[uU]?", expr):
            consts[name] = int(expr.rstrip("uU"), 16)
        else:
            unresolved[name] = expr
    for name, expr in unresolved.items():          # one level of aliasing (kCrt0 = kPsExeEntry)
        if expr in consts:
            consts[name] = consts[expr]
    binds = dict(re.findall(r"\.(\w+)\s*=\s*(k\w+)", text))
    missing = [f"{f}: expected a constant named {K_OF[f]}" for f in ORDER if K_OF[f] not in consts]
    missing += [f"{f}: the GameConfig initialiser does not bind it to any k-constant" for f in ORDER
                if f not in binds]
    if missing:
        raise Refuse("could not read the shipped boot group out of game_config.cpp — refusing to "
                     "compare a SUBSET, because the fields it could not find would then be "
                     "unchecked:\n  " + "\n  ".join(missing))
    return consts, binds


def check_config(img, out, text):
    """THE GATE: diff the SHIPPED constants against the MEASURED ones. Returns a list of failures."""
    consts, binds = parse_config(text)
    fails = []
    print(f"  {'field':<14} {'shipped (game_config.cpp)':<32} {'measured (these bytes)':<20}")
    for f in ORDER:
        k = binds[f]
        if k not in consts:
            fails.append(f"{f}: bound to {k}, which game_config.cpp does not define")
            print(f"  {f:<14} .{f} = {k}  <-- UNDEFINED")
            continue
        shipped, want, bad = consts[k], out[f], False
        if k != K_OF[f]:
            bad = True
            fails.append(f"{f}: bound to {k}, not {K_OF[f]} — a constant bound to the wrong field")
        if shipped != want:
            bad = True
            fails.append(f"{f}: SHIPPED 0x{shipped:08X} (via {k}) != MEASURED 0x{want:08X}")
        print(f"  [{'FAIL' if bad else ' ok '}] {f:<14} {k} = 0x{shipped:08X}"
              f"{'':<{max(1, 14 - len(k))}} 0x{want:08X}")
    # RE-02 routing uses PHYSICAL addresses. A zero or KSEG address makes overlay_router bypass the
    # generated dispatcher and report a convincing `[recomp-MISS]` for functions that already exist.
    # Compare the shipping range to this same PS-EXE header so that failure mode is reproducibly red.
    for field, key, want in (
            ("recMainLo", "kRecMainLo", img.t_addr & 0x1FFFFFFF),
            ("recMainHi", "kRecMainHi", (img.t_addr + img.t_size) & 0x1FFFFFFF)):
        shipped = consts.get(key)
        bound = binds.get(field)
        bad = shipped != want or bound != key
        if bound != key:
            fails.append(f"{field}: bound to {bound or '<nothing>'}, not {key}")
        if shipped != want:
            shown = "<missing>" if shipped is None else f"0x{shipped:08X}"
            fails.append(f"{field}: SHIPPED {shown} != PS-EXE HEADER 0x{want:08X}")
        print(f"  [{'FAIL' if bad else ' ok '}] {field:<14} {key} = "
              f"{('<missing>' if shipped is None else f'0x{shipped:08X}'):<20} 0x{want:08X}")
    return fails


def config_gates(exe_path, text=None):
    """--check-config / --gate-citations, run together: both read the SAME shipping file."""
    try:
        img = Image(exe_path)
        out, cite, tr = measure(img)
    except Refuse as e:
        print(f"[check] REFUSED — nothing was compared, because nothing was measured.\n{e}",
              file=sys.stderr)
        return 2
    if text is None:
        if not os.path.isfile(CONFIG_SRC):
            print(f"[check] REFUSED — no {CONFIG_SRC}; NOTHING was compared.", file=sys.stderr)
            return 2
        text = open(CONFIG_SRC, encoding="utf-8").read()
    print("== SHIPPED vs MEASURED: game/core/game_config.cpp against these bytes ==")
    try:
        fails = check_config(img, out, text)
    except Refuse as e:
        print(f"[check] REFUSED — {e}", file=sys.stderr)
        return 2
    print("== SHIPPED vs MEASURED: the disassembly citation block against these bytes ==")
    cf = gate_citations(img, out, cite, tr, text)
    for l in cf:
        print("  " + l)
    print(f"  [{'FAIL' if cf else ' ok '}] citation block "
          f"({'differs' if cf else 'byte-identical to the generated block'})")
    fails += cf[:1]
    print(f"\n== shipped-vs-measured: {len(fails)} FAILED ==")
    for f in fails:
        print(f"   FAILED: {f}")
    return 1 if fails else 0


def selftest(exe_path):
    """Gate BOTH classes. Positive: the real image yields the fixture. Negative: four mutations and
    two missing-corpus cases must each REFUSE (exit 2) rather than report a value."""
    import tempfile
    fails, ran = [], 0

    def ok(name, cond, detail=""):
        nonlocal ran
        ran += 1
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}" + (f"  {detail}" if detail else ""))
        if not cond:
            fails.append(name)

    print("== POSITIVE class: the real executable must yield the recorded boot group ==")
    try:
        img = Image(exe_path)
    except Refuse as e:
        print(f"  REFUSED: {e}")
        print("  The positive class could not run AT ALL, so this selftest proves nothing about it.")
        return 2
    ok("fixture image identity (sha1)", img.sha1() == FIXTURE_SHA1,
       f"got {img.sha1()}")
    if img.sha1() != FIXTURE_SHA1:
        print("  Refusing to compare against expectations measured on a DIFFERENT image.")
        return 2
    try:
        out, cite, tr = measure(img)
    except Refuse as e:
        print(f"  [FAIL] measurement refused on the real image: {e}")
        return 1
    if not os.path.isfile(CONFIG_SRC):
        print(f"  REFUSED: no {CONFIG_SRC} — the eleven values have no recorded copy to compare "
              f"against, so the positive class would be vacuous.")
        return 2
    cfg_text = open(CONFIG_SRC, encoding="utf-8").read()
    # THE eleven-value positive class: the SHIPPING file against these bytes. There is no third copy.
    try:
        cfails = check_config(img, out, cfg_text)
    except Refuse as e:
        print(f"  [FAIL] could not read the shipped boot group: {e}")
        return 1
    ok("SHIPPED game_config.cpp constants == MEASURED boot group + main routing range",
       not cfails, "; ".join(cfails) if cfails else "11 boot fields + 2 PS-EXE range bounds")
    citf = gate_citations(img, out, cite, tr, cfg_text)
    ok("game_config.cpp's disassembly block is byte-identical to the generated one",
       not citf, citf[0] if citf else "regenerated and matched")
    # The independent witness inside the same image, asserted rather than merely printed.
    tx, txl, da, dal, bs, bsl = out["_snLink"]
    ok("SN link record (independent of crt0's instructions): __bss+__bsslen == bssZeroHi",
       bs + bsl == out["bssZeroHi"], f"0x{bs:08X}+0x{bsl:X} = 0x{bs + bsl:08X}")
    ok("SN link record: __data+__datalen == gp", da + dal == out["gp"],
       f"0x{da:08X}+0x{dal:X} = 0x{da + dal:08X}")
    # THE FACT THAT REFUTED "gap: NONE" — asserted so it cannot quietly stop being true.
    ov = out["_arenaOverlap"]
    ok("the heap arena crt0 declares OVERLAPS the loaded image (it is not free RAM)",
       ov is not None and out["_arenaOverlapNonZero"] > 0,
       f"overlap [0x{ov[0]:08X},0x{ov[1]:08X}) holds {out['_arenaOverlapNonZero']} non-zero bytes"
       if ov else "no overlap — the claim in game_config.cpp must be re-derived")
    thunks, jal_total, rows = out["_biosHeap"]
    ok("the BIOS heap is never allocated from: no malloc/free/calloc/realloc thunk has a caller",
       all(not c for _, fn, _, c in rows if fn != 0x39),
       f"scanned {jal_total} jal sites against {thunks} BIOS A0 thunks; heap thunks: "
       + (", ".join(f"{n}@0x{va:08X}:{len(c)} callers" for va, fn, n, c in rows) or "NONE present"))
    ok("the .bss clear loop actually FIRED (>= 4096 words stored)",
       len([1 for _, a, v in tr.stores if v == 0]) >= 4096,
       f"{len([1 for _, a, v in tr.stores if v == 0])} zero stores")
    ok("crt0 passes a NON-ZERO size in a1 to the libc/heap init",
       out["_initHeapA1"] != 0, f"a1=0x{out['_initHeapA1']:08X}")

    print("== NEGATIVE class: each of these must REFUSE (exit 2), never report a boot group ==")
    with tempfile.TemporaryDirectory(dir=os.path.join(ROOT, "scratch")) as td:
        def mutate(name, patch, expect_word):
            p = os.path.join(td, name)
            b = bytearray(img.data)
            patch(b)
            open(p, "wb").write(bytes(b))
            try:
                m = Image(p)
                o, _, _ = measure(m)
                ok(f"negative: {name}", False,
                   f"REPORTED a boot group instead of refusing (bssZeroLo=0x{o['bssZeroLo']:08X})")
            except Refuse as e:
                txt = str(e).splitlines()[0]
                ok(f"negative: {name}", expect_word.lower() in str(e).lower(),
                   f"refused: {txt[:96]}")

        off = lambda va: va - img.delta
        mutate("bss-loop-store-nopped",
               lambda b: b.__setitem__(slice(off(0x8001F554), off(0x8001F554) + 4), b"\x00\x00\x00\x00"),
               "bss clear loop")
        mutate("unknown-opcode-at-entry",
               lambda b: b.__setitem__(slice(off(img.pc0), off(img.pc0) + 4), b"\x00\x00\x00\x7c"),
               "unmodelled")
        mutate("entry-returns-immediately",
               lambda b: b.__setitem__(slice(off(img.pc0), off(img.pc0) + 8),
                                       b"\x08\x00\xe0\x03\x00\x00\x00\x00"),
               "returned")
        mutate("header-magic-broken",
               lambda b: b.__setitem__(slice(0, 8), b"XX-X EXE"), "PS-X EXE")
        mutate("header-entry-outside-text",
               lambda b: b.__setitem__(slice(0x10, 0x14), struct.pack("<I", 0x00000000)),
               "outside the loaded text")
        p = os.path.join(td, "does-not-exist")
        try:
            Image(p)
            ok("negative: missing executable", False, "did NOT refuse")
        except Refuse as e:
            ok("negative: missing executable", "no executable at" in str(e),
               "refused, naming the path")

    # ── NEGATIVE class for the SHIPPED-vs-MEASURED gate itself. These are the exact edits that used
    # to pass both gates (PROTOCOL.md: kHeapSizePtr +4, kLibcInit -> a real nop). Each mutates the
    # game_config.cpp TEXT and requires the SAME functions the gate calls to report a failure — not a
    # helper beside them. A gate whose red path has never run is decoration.
    print("== NEGATIVE class: a hand-edit of the SHIPPED file must be REPORTED, not tolerated ==")
    import io
    import contextlib

    def cfg_neg(name, old, new, gate):
        if old not in cfg_text:
            ok(f"negative: {name}", False,
               f"anchor {old!r} is not in game_config.cpp — this case exercised NOTHING")
            return
        with contextlib.redirect_stdout(io.StringIO()):
            try:
                f = gate(cfg_text.replace(old, new, 1))
            except Refuse as e:
                f = [str(e).splitlines()[0]]
        ok(f"negative: {name}", bool(f), (f[0][:150] if f else "REPORTED NO FAILURE — the gate is "
                                          "blind to this edit, which is the defect it exists to fix"))

    cfg = lambda t: check_config(img, out, t)
    cit = lambda t: gate_citations(img, out, cite, tr, t)
    cfg_neg("kHeapSizePtr moved +4 (the recorded sabotage)",
            "kHeapSizePtr   = 0x80030FB8u", "kHeapSizePtr   = 0x80030FBCu", cfg)
    cfg_neg("kLibcInit pointed at a real nop (the recorded sabotage)",
            "kLibcInit      = 0x80026864u", "kLibcInit      = 0x8001F564u", cfg)
    cfg_neg("recMainLo zero makes the router bypass generated resident functions",
            "kRecMainLo      = 0x00010000u", "kRecMainLo      = 0x00000000u", cfg)
    cfg_neg("recMainHi moved beyond the PS-EXE text",
            "kRecMainHi      = 0x00062000u", "kRecMainHi      = 0x00062800u", cfg)
    cfg_neg("a right-valued constant bound to the WRONG field (.gp = kLibcInit)",
            ".gp = kGp,", ".gp = kLibcInit,", cfg)
    cfg_neg("a constant deleted outright", "kGameMain      = 0x80042C38u", "kGameMainX = 0u", cfg)
    # Anchor on address+word, not the bare word: the prose above the block quotes `24423678` too, and
    # a bare-word anchor mutated THAT instead and reported nothing. Caught by this very assertion.
    cfg_neg("one raw word in the citation block retyped (the original defect)",
            "8001F548  24423678", "8001F548  24427836", cit)
    cfg_neg("one citation line deleted", f"//   {img.pc0:08X}  3c028003", "// (removed)", cit)
    cfg_neg("the whole citation block removed", CIT_BEGIN, "// nothing to see here", cit)

    print(f"\n== selftest: {ran} assertions, {len(fails)} FAILED ==")
    for f in fails:
        print(f"   FAILED: {f}")
    return 1 if fails else 0


def gate_config():
    """Do game_config.cpp's boot-group static_asserts actually FIRE? Compile the real TU pristine
    (must SUCCEED) and with five mutations (each must FAIL with a static assertion). A compile-time
    check nobody has seen fail is the same untested diagnostic as a runtime one."""
    import json
    import subprocess
    cdb = os.path.join(ROOT, "build", "compile_commands.json")
    src = os.path.join(ROOT, "game", "core", "game_config.cpp")
    if not os.path.isfile(cdb):
        print(f"[gate] REFUSED — no {cdb}.\n"
              f"  NOTHING was compiled and no assert was exercised. Configure first:\n"
              f"    cmake -S . -B build -DCMAKE_BUILD_TYPE=Release "
              f"-DPSXPORT_DIR=\"$(pwd)/external/psxport\"", file=sys.stderr)
        return 2
    entries = [e for e in json.load(open(cdb)) if e["file"].endswith("game/core/game_config.cpp")]
    # A substrate build intentionally compiles this TU twice: once for the generated-code-free seam
    # target and once for vagrant_port. The assert gate must use the seam command because its contract
    # is stable before and after generated/ exists. Select that named target, never whichever duplicate
    # happens to appear first in compile_commands.json.
    seam_entries = [e for e in entries if "CMakeFiles/vagrant_seam.dir/" in e["command"]]
    if len(seam_entries) != 1:
        print(f"[gate] REFUSED — scanned {len(entries)} game_config compile command(s), matched "
              f"{len(seam_entries)} vagrant_seam command(s) (need exactly 1); nothing compiled.",
              file=sys.stderr)
        return 2
    ent, text = seam_entries[0], open(src, encoding="utf-8").read()
    out_dir = os.path.join(ROOT, "scratch", "assertgate")
    os.makedirs(out_dir, exist_ok=True)
    orig_o = "-o CMakeFiles/vagrant_seam.dir/game/core/game_config.cpp.o"
    if orig_o not in ent["command"]:
        print(f"[gate] REFUSED — could not find the object-file flag in the recorded compile command; "
              f"nothing compiled.\n  command: {ent['command'][:200]}", file=sys.stderr)
        return 2

    def compile_(path, tag):
        cmd = ent["command"].replace(orig_o, f"-o {os.path.join(out_dir, tag + '.o')}")
        if path != src:
            cmd = cmd.replace(ent["file"], path)
        r = subprocess.run(cmd, shell=True, cwd=ent["directory"], capture_output=True, text=True)
        msg = next((l for l in r.stderr.splitlines() if "static assertion failed" in l), "")
        return r.returncode, msg, r.stderr

    fails = []

    def ok(name, cond, detail):
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}  {detail}")
        if not cond:
            fails.append(name)

    print("== POSITIVE control: the file as committed must COMPILE ==")
    rc, _, err = compile_(src, "pristine")
    ok("pristine game_config.cpp compiles", rc == 0,
       f"exit={rc}" + ("" if rc == 0 else "\n" + err[:800]))

    print("== NEGATIVE class: each mutation must FAIL with a static assertion ==")
    # Each pair is (what the mutation breaks, old text, new text). The mutations are small and
    # plausible — an off-by-one, a value "corrected" from a reference — because those are the edits
    # the asserts exist to catch, not absurd ones any compiler would reject anyway.
    for name, a, b in [
        ("gp off by one word",       "kGp            = 0x80033674u", "kGp            = 0x80033670u"),
        ("bss end shrunk by a word", "kBssZeroHi     = 0x800401A8u", "kBssZeroHi     = 0x800401A4u"),
        ("heapBase moved off .bss end", "kHeapBase      = 0x800401A8u", "kHeapBase      = 0x800401B0u"),
        ("gameMain outside the image", "kGameMain      = 0x80042C38u", "kGameMain      = 0x80090000u"),
        ("_stacksize no longer adjacent", "kStackTopBase2 = 0x8004913Cu", "kStackTopBase2 = 0x80049140u"),
    ]:
        if a not in text:
            ok(name, False, f"the mutation anchor {a!r} is NOT in game_config.cpp — this gate is "
                            f"stale and exercised NOTHING for this case")
            continue
        p = os.path.join(out_dir, name.replace(" ", "_") + ".cpp")
        open(p, "w", encoding="utf-8").write(text.replace(a, b))
        rc, msg, err = compile_(p, name.replace(" ", "_"))
        ok(name, rc != 0 and bool(msg), f"exit={rc}  {msg.strip()[:120] if msg else 'NO static-assert diagnostic'}")

    print(f"\n== assert gate: {len(fails)} FAILED ==")
    for f in fails:
        print(f"   FAILED: {f}")
    return 1 if fails else 0


def main(argv):
    args = [a for a in argv[1:] if not a.startswith("--")]
    flags = {a for a in argv[1:] if a.startswith("--")}
    exe = args[0] if args and not args[0].startswith("0x") else DEFAULT_EXE
    if "--gate-config" in flags:
        return gate_config()
    if "--check-config" in flags or "--gate-citations" in flags:
        return config_gates(exe)
    if "--emit-citations" in flags:
        try:
            img = Image(exe)
            out, cite, tr = measure(img)
        except Refuse as e:
            print(f"[emit] REFUSED — nothing emitted.\n{e}", file=sys.stderr)
            return 2
        print("\n".join(emit_citations(img, out, cite, tr)))
        return 0
    if "--selftest" in flags:
        rc = selftest(exe)
        print()
        print("== the game_config.cpp assert gate (--gate-config), run as part of the selftest ==")
        return gate_config() or rc
    try:
        img = Image(exe)
        if "--disasm" in flags:
            if len(args) < 1:
                print("--disasm needs <vaddr_hex> [count]", file=sys.stderr)
                return 2
            va = int(args[0], 16)
            n = int(args[1]) if len(args) > 1 else 32
            for i in range(n):
                a = va + 4 * i
                w = img.word_at(a)
                print(f"{a:08X}  {w:08x}  {disasm1(w, a)}")
            return 0
        out, cite, tr = measure(img)
    except Refuse as e:
        print(f"[crt0] REFUSED — nothing measured.\n{e}", file=sys.stderr)
        return 2
    report(img, out, cite, tr)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
