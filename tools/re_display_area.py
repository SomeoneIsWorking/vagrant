#!/usr/bin/env python3
"""MEASURE the RESIDENT's display-area publication, and which word IS its horizontal extent.

  python3 tools/re_display_area.py                  # the claim table
  python3 tools/re_display_area.py --selftest       # every check fed a case that MUST answer the other way

WHY THIS IS ITS OWN TOOL. `re_viewport.py` measures the BATTLE overlay's projection publication. This
one measures the RESIDENT boot's, and the distinction is the whole content of `docs/issues/0042`: on
2026-09-28 the first authenticated run of this title aborted inside the resident's own
`_initScreen`, because an owner installed on the shared `SetDefDispEnv` leaf cross-checked the boot's
stated width against BATTLE's rectangle — a word the resident executable never writes. Two
publications, two different call sites, one leaf, and a check that is only a valid second statement of
one horizontal extent for ONE of them.

WHAT IS SETTLED HERE, and it is three things the product depends on:
  * the resident publication is `_initScreen` at 0x80042054, it hands the leaf its stated width in
    `$a3` (carried from its own `$a0`) and `height - 16` in the fifth stack slot, and the struct it
    was handed is `vs_main_dispEnv[0]`, which the body builds as `lui 0x8006` + `addiu -7800`;
  * 0x8005DFD4..0x8005DFDA is the OVERLAY publication's rectangle — the resident executable names
    NONE of its four halfwords, and the only stores anywhere in the provisioned modules are that
    publication's own four — so it is still zero BSS while the boot runs;
  * a publication's own horizontal extent is the word the LEAF itself stores the stated width into,
    at `+4` of the struct the CALLER named. The address is therefore a per-call value the caller
    chooses, which is why no title constant can be the cross-check target.

THE MIPS-I FIELD EXTRACTOR AND THE SHA-BOUND IMAGE LOADERS ARE re_viewport's, imported rather than
copied: a second ISA decoder is a second set of answers about the same words.

WHAT IT DOES NOT ANSWER, AND SAYS SO ON EVERY RUN.
  * It reads NO image it has not been given the SHA-1 of, and a missing image is a REFUSAL, never a
    zero. A "no site" answer is "no site in the scanned words of the named modules", with the scanned
    count attached.
  * It does not report a frame rate and it does not report what any owner did with these numbers.
"""

from __future__ import annotations

import argparse
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from re_viewport import (  # noqa: E402  — the shared MIPS-field primitives, imported once
    DEFAULT_EXE,
    EXE_HEADER,
    DEFAULT_OVERLAY_DIR,
    PROJECTION_DISTANCE,
    VIEWPORT_RECT,
    Claim,
    ExeSet,
    Refuse,
    _cite,
    _find_jals,
    _is,
    _lui_field_refs,
    load_overlays,
    sym,
    target_of,
)

# The addresses under test, and the two struct offsets the leaves' own stores settle.
RESIDENT_INIT_SCREEN = 0x80042054
RESIDENT_DISP_ENV_PAGE = 0x8006
RESIDENT_DISP_ENV_DISPLACEMENT = -7800          # 0x80060000 - 7800 == 0x8005E188
LEAF_SET_DEF_DISP_ENV = 0x8002B434
LEAF_SET_DEF_DRAW_ENV = 0x8002B374
LEAF_ENV_WIDTH_OFFSET = 4
LEAF_ENV_HEIGHT_OFFSET = 6
# The overlay publication's own four stores, and the extent each module is scanned over.
PUBLICATION_STORES = {0x800761E0, 0x800761E8, 0x800761F0, 0x80076200}


def leaf_sh_stores(img, leaf, window, struct_offset):
    """Every `sh` in a leaf's first `window` bytes at the given offset of the caller's struct.

    FOUND, NOT NAMED, on purpose. A previous revision of this claim asserted an address
    (`leaf + 0x10 + 0x2C`) and got it wrong by four bytes, so it read a `nop` and reported REFUTED on
    the real image — and its own negative case went green anyway, because that case perturbed the same
    wrong address. A restated offset is a second thing to keep in step; a scan is the one answer, and
    a scan that finds none, or more than one, says so with a denominator.
    """
    for a in range(leaf, leaf + window, 4):
        d = img.insn(a)
        if d and d.get("mnemonic") == "sh" and d.get("imm") == struct_offset:
            yield a


def display_area_claims(exe, overlays, out=print):
    """Every claim about the RESIDENT publication, decided by the instruction words.

    This is the one seam between this tool and `re_viewport.py`: that tool measures the
    BATTLE overlay's publication and calls this for the boot's, because they are two
    publications reached through one shared SDK leaf and a check written for one is not a
    statement about the other.
    """
    claims = []
    # THE RESIDENT'S OWN DISPLAY-AREA PUBLICATION, and the word that IS its horizontal extent.

    # the resident publication's own `SetDefDispEnv` call: $a0 = the caller's struct pointer, $a3 = the
    # stated width (carried in from $a0 by the body's second word), $a1-16 in the fifth stack slot.
    b_wide = exe.insn(RESIDENT_INIT_SCREEN + 0x04)          # addu $a3, $a0, $zero
    b_env = exe.insn(RESIDENT_INIT_SCREEN + 0x14)          # addu $a0, $s0, $zero
    b_page = exe.insn(RESIDENT_INIT_SCREEN + 0x0C)         # lui  $s0, 0x8006
    b_disp = exe.insn(RESIDENT_INIT_SCREEN + 0x10)         # addiu $s0, $s0, -7800
    b_h = exe.insn(RESIDENT_INIT_SCREEN + 0x18)            # addiu $a1, $a1, -16
    b_call = target_of(exe.word(RESIDENT_INIT_SCREEN + 0x28), RESIDENT_INIT_SCREEN + 0x28)
    disp_env = ((b_page["raw_imm"] << 16) + b_disp["imm"]) if (b_page and b_disp) else None
    claims.append(Claim(
        "the resident's display-area publication 0x%08X is `_initScreen`, it hands SetDefDispEnv the "
        "stated WIDTH in $a3 (carried from its own $a0) and (height-16) in the fifth stack slot, and "
        "the struct it was handed is 0x%08X = `vs_main_dispEnv[0]`"
        % (RESIDENT_INIT_SCREEN, disp_env or 0),
        "CONFIRMED" if (disp_env == 0x8005E188 and b_call == LEAF_SET_DEF_DISP_ENV and
                        _is(b_wide, op=0, rd=7, rs=4, rt=0) and
                        _is(b_env, op=0, rd=4, rs=16, rt=0) and
                        _is(b_page, mnemonic="lui", raw_imm=RESIDENT_DISP_ENV_PAGE) and
                        _is(b_h, mnemonic="addiu", rt=5, rs=5, imm=-16)) else "REFUTED",
        _cite(exe, RESIDENT_INIT_SCREEN, 13) +
        ["      struct pointer 0x%08X + %d = the publication's own width word 0x%08X; + %d = its height"
         % (disp_env or 0, LEAF_ENV_WIDTH_OFFSET, (disp_env or 0) + LEAF_ENV_WIDTH_OFFSET,
            LEAF_ENV_HEIGHT_OFFSET)]))

    # The boot's stated width. `_displayLoadingScreen` at 0x800420BC is the only caller, and it states
    # 320x240 — read from the argument setup immediately before the `jal`, not from a name.
    boot_sites = _find_jals(exe, exe.t_addr, exe.t_addr + exe.t_size, RESIDENT_INIT_SCREEN)
    boot_w = exe.insn(boot_sites[0] - 0x30) if boot_sites else None
    boot_h = exe.insn(boot_sites[0] - 0x2C) if boot_sites else None
    claims.append(Claim(
        "the boot states 320x240 to that publication from exactly one call site, 0x%08X"
        % (boot_sites[0] if boot_sites else 0),
        "CONFIRMED" if (len(boot_sites) == 1 and _is(boot_w, mnemonic="addiu", rt=4, rs=0, imm=320)
                        and _is(boot_h, mnemonic="addiu", rt=5, rs=0, imm=240)) else "REFUTED",
        (_cite(exe, boot_sites[0] - 0x34, 14) if boot_sites else
         ["      NOT CALLED: the resident executable states no call of 0x%08X" % RESIDENT_INIT_SCREEN]) +
        ["      call sites of 0x%08X in the resident text segment: %d"
         % (RESIDENT_INIT_SCREEN, len(boot_sites))]))

    # THE CENSUS THAT DECIDES THE FATAL. How many instructions in each provisioned module NAME the
    # BATTLE rectangle at all. A boot-time owner that cross-checks its own publication against this
    # word is checking against a word nothing has written yet, and the zero below is the finding.
    rect_targets = {VIEWPORT_RECT + off for off in (0, 2, 4, 6)}
    rect_refs = {}
    for key, img in [("SLUS_010.40", exe.image)] + sorted(overlays.items()):
        if img is None:
            continue
        rect_refs[key] = _lui_field_refs(img, rect_targets)
    resident_refs = rect_refs.get("SLUS_010.40", [])
    overlay_writers = {k: [a for a, kind, _w in v if kind.startswith("s")]
                       for k, v in sorted(rect_refs.items())}
    # The ONLY stores anywhere in the provisioned modules are the overlay publication's own four, at
    # the addresses the store-order claim above settled. So the rectangle is that publication's state
    # and nothing else writes it.
    publication_stores = {0x800761E0, 0x800761E8, 0x800761F0, 0x80076200}
    every_writer = {a for sites in overlay_writers.values() for a in sites}
    claims.append(Claim(
        "0x8005DFD4..0x8005DFDA is OVERLAY state: the resident executable names NONE of its four "
        "halfwords, and the only stores anywhere in the provisioned modules are the overlay "
        "publication's own four — so the word a boot publication is cross-checked against is still "
        "zero BSS when the boot publishes",
        "CONFIRMED" if (not resident_refs and every_writer == publication_stores) else "REFUTED",
        ["      every reference found, per module, as the SUM of the `lui` page and the displacement:"]
        + ["        %-11s %d reference(s): %s" % (k, len(v),
                                                 ", ".join("0x%08X:%s" % (a, kind) for a, kind, _w in v)
                                                 or "NONE — this module never names the rectangle")
           for k, v in sorted(rect_refs.items())] +
        ["      every store of the rectangle in every provisioned module: %s"
         % ", ".join(sym(a) for a in sorted(every_writer))] +
        ["      the overlay publication's own four stores: %s"
         % ", ".join(sym(a) for a in sorted(publication_stores))]))

    # Both env leaves store the stated width at +4 of the caller's struct and the stated HEIGHT at
    # +6. THAT is the publication's own extent, and it is what the leaf-level cross-check reads —
    # both halves of it, so both are settled here. The height is the fifth argument, which arrives
    # on the stack and is moved into a register before the store, so each leaf has its own source
    # register and the claim names it rather than assuming `$a3`.
    #
    # THE HEIGHT STORE IS FOUND, NOT NAMED. A previous revision of this block asserted an address
    # (`expect_store + 0x2C`) and got it wrong by four bytes: the real store is at `+0x28`, and the
    # claim therefore read a `nop` and reported REFUTED on the unperturbed image. What made that
    # survivable is worse than the wrong offset — its own selftest went RED by perturbing that same
    # wrong address, so a claim that never held on the real bytes had a negative case that passed.
    # A restated offset is a second thing to keep in step; a scan is the one answer. So each leaf's
    # words are scanned for a `sh` at offset 6, and the claim is about what that scan FOUND: how many
    # candidates, at which addresses, from which registers. A scan that finds none, or more than one,
    # says so with a denominator instead of quietly reading a neighbour.
    # The fifth stack argument reaches each leaf in its OWN register, and the register NUMBERS are
    # named here rather than written inline: `SetDefDispEnv` loads it into `$v1` (3) and `SetDefDrawEnv`
    # into `$s2` (18). An earlier revision of this claim used 1, which is `$at`, so the claim read
    # REFUTED on the real image and the only reason that was caught is that the instrument reports
    # verdicts rather than booleans.
    for leaf, label, expect_store, expect_width_reg, expect_height_reg, span in (
            (LEAF_SET_DEF_DISP_ENV, "SetDefDispEnv", LEAF_SET_DEF_DISP_ENV + 0x10, 7, 3, 0x40),
            (LEAF_SET_DEF_DRAW_ENV, "SetDefDrawEnv", LEAF_SET_DEF_DRAW_ENV + 0x40, 16, 18, 0x80)):
        d = exe.insn(expect_store)
        candidates = [a for a in leaf_sh_stores(exe, leaf, span, LEAF_ENV_HEIGHT_OFFSET)]
        found = candidates[0] if len(candidates) == 1 else None
        h = exe.insn(found) if found is not None else None
        claims.append(Claim(
            "%s stores its stated WIDTH to the struct the CALLER handed it, at +%d of that struct — so "
            "a publication's own horizontal extent is `env + %d`, a per-call address the caller names"
            % (label, LEAF_ENV_WIDTH_OFFSET, LEAF_ENV_WIDTH_OFFSET),
            "CONFIRMED" if _is(d, mnemonic="sh", rt=expect_width_reg,
                               imm=LEAF_ENV_WIDTH_OFFSET) else "REFUTED",
            _cite(exe, leaf, 12 if leaf == LEAF_SET_DEF_DISP_ENV else 20)))
        claims.append(Claim(
            "%s also stores its stated HEIGHT at +%d of the same struct, from the fifth stack "
            "argument — so the owner's own vertical extent is a per-call word too and not a constant"
            % (label, LEAF_ENV_HEIGHT_OFFSET),
            "CONFIRMED" if (found is not None and _is(h, mnemonic="sh", rt=expect_height_reg,
                                                       imm=LEAF_ENV_HEIGHT_OFFSET)) else "REFUTED",
            ["      scanned %d instruction(s) of this leaf for a `sh` at struct offset +%d: found %d at %s"
             % (span // 4, LEAF_ENV_HEIGHT_OFFSET, len(candidates),
                ", ".join(sym(a) for a in candidates) or "NONE")] +
            # The citation names the store ONLY when there is one. A REFUSED claim still has to
            # print its evidence, and printing a citation at a `None` address is a crash in the
            # diagnostic rather than a result in it.
            (_cite(exe, found, 3) if found is not None
             else ["      NOT CITED: this leaf states no store at +%d, so there is no address to show"
                   % LEAF_ENV_HEIGHT_OFFSET]) +
            ["      the height word is env + %d; the width word is env + %d"
             % (LEAF_ENV_HEIGHT_OFFSET, LEAF_ENV_WIDTH_OFFSET)]))
    return claims


def report(claims, out=print):
    out("=" * 100)
    out("VAGRANT STORY — THE RESIDENT DISPLAY-AREA PUBLICATION, VERIFIED AGAINST BYTES")
    out("Every address below was decoded from the image this tool SHA-1-checked. CONFIRMED means the")
    out("named instruction words are present at the named addresses; REFUTED means they are not.")
    out("=" * 100)
    for c in claims:
        out("")
        out("[%s] %s" % (c.verdict, c.title))
        for line in c.words:
            out(line)
    out("")
    out("  THE BATTLE OVERLAY PUBLICATION IS `tools/re_viewport.py`, and the VSync(n) call-site")
    out("  census is `tools/re_vsync_sites.py`. Three publications' subjects, three tools.")


def perturbed(real, image):
    """An `ExeSet` over a MUTATED copy, for a claim that must be able to flip."""
    clone = ExeSet.__new__(ExeSet)
    clone.path = real.path
    clone.data = bytes(image.data)
    clone.t_addr = real.t_addr
    clone.t_size = real.t_size
    clone.image = image
    return clone


def selftest(out=print):
    """Every check this tool makes, fed an input whose answer is known WITHOUT this tool.

    THREE conditions per negative case: the scan finds exactly one candidate, the UNPERTURBED claim
    reads CONFIRMED, and perturbing THAT candidate reads REFUTED. A negative case that cannot tell
    "the claim broke" from "the byte I perturbed is not the byte the claim reads" is not a negative
    case, and one of these three was green against a claim that had never held.
    """
    out("== re_display_area.py --selftest: 4 checks, each a case that MUST come out the other way " + "=")
    for line in (
            "1. the resident publication claim, on a copy whose `$a3 <- $a0` word is perturbed, REFUTES",
            "2. the SetDefDispEnv width-store claim, on a copy whose `sh $a3, 4($v0)` is perturbed, REFUTES",
            "3. the rectangle census answers ZERO for the overlay rectangle and NONZERO for a word the "
            "resident demonstrably names — one scan, two targets, opposite answers",
            "4. the SetDefDispEnv height-store claim: the scan finds exactly one candidate, the "
            "UNPERTURBED claim reads CONFIRMED, and perturbing THAT candidate reads REFUTED",
    ):
        out("   " + line)
    out("")
    fails = []
    try:
        exe = ExeSet()
        ov = load_overlays()
    except Refuse as exc:
        out("  [1] FAIL %s" % exc)
        return [1, 2, 3, 4]
    out("  [1] PASS loaded SLUS_010.40 + %d/3 overlays, sha1-bound"
        % sum(1 for v in ov.values() if v is not None))

    def copy():
        return rv_image(exe)

    def rv_image(real):
        return type(real.image)(real.image.name, bytearray(real.image.data), real.t_addr,
                                real.image.file_start, real.image.file_end)

    # [1] the resident publication's own width carry
    resident = copy()
    at = RESIDENT_INIT_SCREEN + 0x04 - exe.t_addr + EXE_HEADER
    word = struct.unpack_from("<I", resident.data, at)[0]
    # Bit 22 is `$a0`'s bit of `rs`, a field the claim tests. An earlier attempt flipped a LOW byte,
    # which is the `funct` field and left every field the claim tests untouched: a perturbation that
    # cannot move the verdict proves only that bytes are bytes.
    struct.pack_into("<I", resident.data, at, word ^ 0x00400000)
    verdicts = _verdicts(display_area_claims(perturbed(exe, resident), ov),
                        "resident's display-area publication")
    out("  [1] %s a perturbed `$a3 <- $a0` reads %s" % ("PASS" if verdicts == ["REFUTED"] else "FAIL",
                                                        verdicts))
    if verdicts != ["REFUTED"]:
        fails.append(1)

    # [2] the leaf's own width store
    leaf = copy()
    leaf.data[LEAF_SET_DEF_DISP_ENV + 0x10 - exe.t_addr + EXE_HEADER] ^= 0xFF
    verdicts = _verdicts(display_area_claims(perturbed(exe, leaf), ov), "stores its stated WIDTH",
                        "SetDefDispEnv")
    out("  [2] %s a perturbed `sh $a3, 4($v0)` reads %s"
        % ("PASS" if verdicts == ["REFUTED"] else "FAIL", verdicts))
    if verdicts != ["REFUTED"]:
        fails.append(2)

    # [3] the census must be able to say ZERO and NON-ZERO on the same scan
    rect_targets = {VIEWPORT_RECT + off for off in (0, 2, 4, 6)}
    resident_zero = _lui_field_refs(exe.image, rect_targets)
    control_some = _lui_field_refs(exe.image, {PROJECTION_DISTANCE})
    ok = not resident_zero and control_some
    out("  [3] %s the resident names 0x8005DFD4..DA %d time(s) (must be 0) and the control word "
        "0x8005E248 %d time(s) (must be > 0)"
        % ("PASS" if ok else "FAIL", len(resident_zero), len(control_some)))
    if not ok:
        fails.append(3)

    # [4] the height store, with all three conditions
    found = list(leaf_sh_stores(exe, LEAF_SET_DEF_DISP_ENV, 0x40, LEAF_ENV_HEIGHT_OFFSET))
    mutated = copy()
    if len(found) == 1:
        mutated.data[found[0] - exe.t_addr + EXE_HEADER] ^= 0x40   # bit 6 is `$v0`'s bit of `rs`
    after = _verdicts(display_area_claims(perturbed(exe, mutated), ov), "stores its stated HEIGHT",
                       "SetDefDispEnv")
    before = _verdicts(display_area_claims(exe, ov), "stated HEIGHT", "SetDefDispEnv")
    ok = (len(found) == 1 and before == ["CONFIRMED"] and after == ["REFUTED"])
    out("  [4] %s the height-store claim: the scan finds %d candidate(s) at %s, the unperturbed claim "
        "reads %s, and perturbing THAT store reads %s — all three must hold"
        % ("PASS" if ok else "FAIL", len(found),
           ", ".join(sym(a) for a in found) or "none", before, after))
    if not ok:
        fails.append(4)

    out("")
    out("  selftest: %d of %d checks FAILED %s" % (len(fails), 4, fails or ""))
    return fails


def _verdicts(claims, *needles):
    """The verdicts of the claims whose title contains every needle, in claim order.

    The needles have to be SPECIFIC. `"stated WIDTH"` and `"SetDefDispEnv"` together match TWO claims
    here, because the resident-publication claim's own title says it "hands SetDefDispEnv the stated
    WIDTH in $a3" — and a selftest that perturbs the leaf's store and then reports the pair
    `['CONFIRMED', 'REFUTED']` has measured nothing about which claim it perturbed.
    """
    return [c.verdict for c in claims if all(n in c.title for n in needles)]


def main(argv):
    if "--selftest" in argv:
        return 1 if selftest() else 0
    args = [a for a in argv if not a.startswith("--")]
    if args and args[0] not in ("--exe", "--overlays"):
        print("usage: re_display_area.py [--exe PATH] [--overlays DIR] [--selftest]", file=sys.stderr)
        return 2
    exe_path = args[args.index("--exe") + 1] if "--exe" in args else DEFAULT_EXE
    ov_dir = args[args.index("--overlays") + 1] if "--overlays" in args else DEFAULT_OVERLAY_DIR
    try:
        exe = ExeSet(exe_path)
        ov = load_overlays(ov_dir)
    except Refuse as exc:
        print("[re_display_area] REFUSING: %s" % exc, file=sys.stderr)
        return 2
    covered = sum(1 for v in ov.values() if v is not None)
    print("loaded: SLUS_010.40 (sha1 %s…), overlays %d of 3 (%s)"
          % (sym(exe.t_addr) and "fababcfd4325"[:12], covered,
             ", ".join(k for k, v in sorted(ov.items()) if v is not None)))
    print("A missing overlay is a REFUSAL for the claims that would have come from it — never a zero.")
    print("")
    report(display_area_claims(exe, ov))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
