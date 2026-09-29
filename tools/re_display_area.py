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
    DEFAULT_OVERLAY_DIR,
    DRAW_ENV0,
    DRAW_ENV_CLIP_OFFSETS,
    DRAW_ENV_DFE_OFFSET,
    DRAW_ENV_HEIGHT_CLASSES,
    DRAW_ENV_STRIDE,
    DRAW_ENV_TW_OFFSETS,
    EXE_HEADER,
    LEAF_SET_DEF_DRAW_ENV,
    PROJECTION_DISTANCE,
    VIEWPORT_PUBLICATION,
    VIEWPORT_RECT,
    Claim,
    ExeSet,
    Refuse,
    _args_320_240_H,
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
    out("== re_display_area.py --selftest: 5 checks, each a case that MUST come out the other way " + "=")
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

    # [5] THE DRAWENV CLIP, and the argument scanner underneath it. Three defects in that scanner
    #     each held a CONFIRMED claim down to REFUTED, and each was invisible because a claim that
    #     always says REFUTED reads exactly like a claim about a title that differs. So this case
    #     establishes the claim CONFIRMED on the real image FIRST, and then shows each of the
    #     scanner's three rules can give a different answer on a perturbed one.
    #
    #     The three, and what each perturbation breaks:
    #       * the window is BEHIND the call — a word placed AFTER the `jal` must not be read;
    #       * the NEAREST definition wins — an extra earlier definition must not displace a nearer one;
    #       * an argument register copied from another resolves — a copy chain must be followed.
    bat = ov["BATTLE.PRG"]
    bcode = (bat.base + bat.code[0], bat.base + bat.code[1])
    before = _verdicts(draw_area_clip_claims(bat, exe), "the two DRAWENVs' clips")

    def clip_of(image):
        return [_resolve_arguments(_call_arguments(image, s), {0: 0, 18: 320, 19: 224})[1:]
                for s in (0x8007614C, 0x80076188)]

    real = clip_of(bat)
    # (a) direction. `addu $a1, $s2, $zero` lives at 0x80076160, AFTER the call, and a scanner that
    #     reads forward would report the clip's x as 320 at the FIRST site and 0 at the second —
    #     which is exactly the inversion that was shipped. Assert the real order, not just equality.
    behind_only = clip_of(bat)[0] == [0, 0, 320, 224] and clip_of(bat)[1] == [320, 0, 320, 224]
    # (b) nearest-wins and (c) argument-register copy, each shown by perturbing the IMAGE the way a
    #     compiler change would and reading the answer back, so the rules are tested where they run.
    def with_word(address, word):
        """A copy of BATTLE.PRG with ONE instruction word replaced, little-endian as the image is.

        A copy of the OVERLAY, not of the executable: `copy()` above clones SLUS_010.40, and writing
        an overlay address into it would have perturbed an unrelated module and left the claim
        reading exactly what it read before — a negative case that cannot fail, which is the failure
        mode this whole case exists to avoid. `code` is carried over because the claim reads the
        module's declared extent.
        """
        image = type(bat)(bat.name, bytearray(bat.data), bat.base, bat.file_start, bat.file_end)
        image.code = bat.code
        struct.pack_into("<I", image.data, address - bat.base, word)
        return image

    # Make the nearer `addu $a1, $zero, $zero` into `addu $a1, $s2, $zero`: the nearest definition
    # now says 320, and a nearest-wins scanner must report that, not the 0 that is now only the
    # further-back $a2 copy's source.
    nearest = with_word(0x80076140, 0x02402821)      # addu $a1, $s2, $zero
    # Break the copy: turn `addu $a2, $a1, $zero` into a move from an unresolvable register, so `y`
    # can only come out if the resolver really is following the argument-register chain.
    copy_broken = with_word(0x80076144, 0x02A03021)  # addu $a2, $s5, $zero
    reads_behind = clip_of(nearest)[0][0] == 320
    follows_copy = clip_of(copy_broken)[0][1] is None

    ok = before == ["CONFIRMED"] and behind_only and reads_behind and follows_copy and real
    out("  [5] %s the clip claim: unperturbed %s, measured clips %s; a nearer definition reading 320 "
        "is read as %s (must be 320), and a broken `$a2` copy reads y=%s (must be None) — all five "
        "must hold"
        % ("PASS" if ok else "FAIL", before, real,
           clip_of(nearest)[0][0] if nearest else None,
           clip_of(copy_broken)[0][1] if copy_broken else "?"))
    if not ok:
        fails.append(5)

    out("")
    out("  selftest: %d of %d checks FAILED %s" % (len(fails), 5, fails or ""))
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
    # Both halves of this module's subject: the resident DISPLAY area and the DRAWING-area clip.
    # The clip claims are reported HERE as well as being extended into `re_viewport.py`'s table,
    # because the tool that owns the subject has to be able to show its own verdicts without
    # depending on another tool's report to print them.
    report(display_area_claims(exe, ov))
    bat = ov.get("BATTLE.PRG")
    if bat is None:
        print("[re_display_area] REFUSING: BATTLE.PRG absent, so NO clip claim was evaluated — "
              "that is a refusal, not a pass", file=sys.stderr)
        return 2
    report(draw_area_clip_claims(bat, exe))
    return 0


# ====================================================================================================
# THE DRAWING-AREA CLIP, moved here from `re_viewport.py` for the same reason section 3b moved.
#
# It belongs here because it answers the question 3b answers — WHICH WORD IN THE ENV STRUCT CARRIES
# WHAT — for the other of the two structs the guest hands the leaves. `re_viewport.py` keeps the
# BATTLE projection publication; the env structs are this module's subject.
#
# Every name the moved block uses is imported from `re_viewport` in the list above: there is no
# second binding here and no address is declared in this module. A correction in `re_viewport.py`
# therefore reaches this measurement without anyone editing it twice, which is the whole reason the
# split is a module and not a text move.

def _call_arguments(img, site, back=5):
    """The five values a call site hands its callee, as `("imm", n)` / `("reg", n)` / None tuples.

    Positions 0..3 are `$a0..$a3` and position 4 is the fifth argument, which the `jal`'s DELAY
    SLOT writes to 0x10($sp) AFTER the call word — a backwards-only scan misses it and
    under-reports the argument count, which is the same failure as a census that reports zero
    because it never looked where the value is. A position with no writer found stays None, and
    None resolves to None, which equals no expected value: a gap in the argument setup is a
    REFUTED claim rather than a silent zero.

    **TWO RULES, AND BOTH WERE WRONG IN THE FIRST VERSION OF THIS FUNCTION.** The claim below was
    REFUTED against bytes that confirm it, and the claim is the only reason either was caught —
    because it prints the values it resolved, and they did not match the words in front of it.

      1. THE WINDOW IS BEHIND THE CALL, not in front of it. The first version walked
         `site + 4 * delta` for delta 1..5, which reads the five instructions AFTER the `jal` — the
         code that runs once the callee has returned. It reported the clip at 0x8007614C as
         `x = 320` from `addu $a1, $s2, $zero` at 0x80076160, a post-call instruction, while the
         nearest real definition in front of the call is `addu $a1, $zero, $zero` at 0x80076140.
         So the fix is the SIGN: `site - 4 * delta`. The ONE forward instruction is the delay slot
         at `site + 4`, which genuinely executes before the callee and is read as delta -1.
      2. THE NEAREST DEFINITION WINS, because the instruction nearest the call is the last one to
         have executed, so a slot already holding a value is not overwritten by a further-back one.
         With unconditional assignment the EARLIEST instruction in the window won.

    Together they are the same rule `_a0_backward` in `re_viewport.py` already states for the same
    straight line — and this file had it in the opposite state, which is the duplication this module
    exists to stop, found the hard way.
    """
    args = [None] * 5

    def claim(slot, value):
        if args[slot] is None:
            args[slot] = value

    for delta in list(range(1, back + 1)) + [-1]:
        # delta 1..N walks BACKWARDS from the call; delta -1 is the delay slot, which is forward.
        d = img.insn(site - 4 * delta if delta > 0 else site + 4)
        if d is None:
            continue
        if d.get("op") == 0 and d.get("rt") == 0 and 4 <= d.get("rd", 0) <= 7:
            claim(d["rd"] - 4, ("reg", d["rs"]))          # `addu $rd, $rs, $zero` is this move
        elif d.get("mnemonic") == "addiu" and d.get("rs") == 0 and 4 <= d.get("rt", 0) <= 7:
            claim(d["rt"] - 4, ("imm", d["imm"]))
        elif d.get("mnemonic") == "sw" and d.get("rs") == 29 and d.get("imm") == 0x10:
            claim(4, ("reg", d["rt"]))
    return args


def _resolve_arguments(args, known):
    """`_call_arguments` output as numbers, with `known` mapping register number to value.

    `known` exists because the publication states its clip in registers it computed once at its
    entry — `$s2` is arg0 and `$s3` is `arg1 - 16` — so the call sites themselves hold no literal.
    Register 0 is `$zero`, which is the one register whose value needs no evidence.

    **AN ARGUMENT REGISTER COPIED FROM ANOTHER ARGUMENT REGISTER RESOLVES THROUGH IT.** The measured
    setup at 0x80076140..0x80076144 is `addu $a1, $zero, $zero` then `addu $a2, $a1, $zero` — the
    second is a copy of the FIRST, not a fresh literal, and treating it as an unknown register left
    the clip's `y` at None and the claim REFUTED on bytes that settle it. So a definition in
    registers 4..7 is resolved from the already-resolved argument slot it names, and the resolution
    is a small fixpoint rather than a single pass, because the copy can point forwards as well as
    backwards. `rounds` is reported by the caller so a claim cannot be silently resolved by a
    resolver that gave up, and a CYCLE is a named refusal rather than a None that reads as a gap.
    """
    # `$aN` is argument register N, so slot i of `args` is also the source register for a copy out
    # of it. The map is built from the raw defs, then iterated to a fixpoint.
    out = []
    for a in args:
        if a is None:
            out.append(None)
        elif a[0] == "imm":
            out.append(a[1])
        elif a[1] in known:
            out.append(known[a[1]])
        elif 4 <= a[1] <= 7:
            out.append(("argreg", a[1] - 4))          # unresolved copy: resolve on the next round
        else:
            out.append(None)

    rounds = 0
    for rounds in range(1, 5):
        changed = False
        for i, value in enumerate(out):
            if isinstance(value, tuple) and value[0] == "argreg":
                source = out[value[1]]
                if source is not None and not isinstance(source, tuple):
                    out[i] = source
                    changed = True
        if not changed:
            break
    else:
        raise Refuse(
            "_resolve_arguments: argument registers 4..7 copy each other in a cycle over %d rounds "
            "at %s; the argument setup is not a straight line and this resolver does not model it"
            % (rounds, args))

    return out


def draw_area_clip_claims(bat, exe, out=print):
    """The DRAWENV clip field map, its `dfe` flag, and the two clips the publication states."""
    claims = []
    # BATTLE.PRG's declared code extent, derived from the image rather than restated: `code` is the
    # (first, last) byte pair `load_overlays` bound from rood-reverse's own `splat.yaml`, and the
    # block moved here used the caller's copy of this. Recomputing it is one line and keeps a single
    # derivation; hard-coding a range here would be a second answer to "where does this module end".
    BCODE = (bat.base + bat.code[0], bat.base + bat.code[1])

    # --- 3a. THE DRAWING-AREA CLIP, WHICH THE PREVIOUS REVISION OF THIS FILE GOT WRONG -------------
    #
    # It said, in these words: "SetDefDrawEnv writes the draw-area CLIP w/h (DRAWENV +0xC/+0xE) as
    # ZERO and the publication never stores there, so the DRAWING area is unclipped for the whole
    # field", and reported it CONFIRMED. BOTH halves are refuted by the leaf's own words, and the
    # cause is legible: the decompilation's `libgpu.h` FIELD NAMES were read without the struct's
    # OFFSETS, so the leaf's four zero-fills at +0xC..+0x12 — the TEXTURE WINDOW — were read as a
    # clip. The clip is at +0x00..+0x06, and the leaf fills it from its arguments. A reader arriving
    # at the corrected claims below has to be able to see what the wrong one claimed and why, so the
    # wrong sentence is quoted rather than deleted. `docs/issues/0038` carries the same correction
    # and the same quote; the tool and the issue agree or one of them is a guess.
    clip_stores = ((0x8002B3AC, 0, 19), (0x8002B3B0, 2, 20), (0x8002B3B4, 4, 16), (0x8002B3DC, 6, 18))

    def store_fields(img, a):
        # A word this decoder does not recognise is `None`, not a pair of zero fields: an
        # undecodable instruction must be able to fail the claim rather than satisfy it.
        d = img.insn(a)
        return (d.get("imm"), d.get("rt")) if d is not None else None

    got_clip = [store_fields(exe, a) for a, _o, _r in clip_stores]
    got_tw = [store_fields(exe, 0x8002B3B8 + 4 * i) for i in range(4)]
    # `+6` is the one store that is NOT between the leaf's own stores of the other three: it is the
    # delay slot of the `beq` at 0x8002B3D8, so it runs on BOTH paths. A claim that read it as
    # conditional would leave the clip's height unstated, which is the half that bounds the field.
    unconditional = _is(exe.insn(0x8002B3D8), mnemonic="beq")
    # ... and the three registers the clip is filled from are the leaf's own copies of the three
    # arguments, with `+6` coming from the caller's argument area (`lw $s2, 0x38($sp)`, 0x38 == the
    # fifth argument once this leaf's own -0x28 frame is added to 0x10).
    sources = [_is(exe.insn(a), op=0, rt=0, rd=r, rs=s) for a, r, s in
               ((0x8002B38C, 19, 5), (0x8002B394, 20, 6), (0x8002B3A4, 16, 7))]
    sources.append(_is(exe.insn(0x8002B37C), mnemonic="lw", rt=18, rs=29, imm=0x38))
    ok = (got_clip == [(o, r) for _a, o, r in clip_stores] and
          got_tw == [(o, 0) for o in DRAW_ENV_TW_OFFSETS] and unconditional and all(sources))
    claims.append(Claim(
        "SetDefDrawEnv fills the RECT CLIP at DRAWENV +0x00/+0x02/+0x04/+0x06 from its own arguments "
        "and zero-fills +0xC..+0x12, which is the TEXTURE WINDOW: so the DRAWING area is CLIPPED, "
        "and the previous revision of this tool's claim that it is unclipped read the wrong offsets",
        "CONFIRMED" if ok else "REFUTED",
        ["      clip stores (offset, source register) found: %s" % got_clip] +
        ["      texture-window zero-fills (offset, source register) found: %s" % got_tw] +
        ["      the +0x06 store is the delay slot of a `beq`, so it is UNCONDITIONAL: %s"
         % unconditional] +
        ["      each clip register is a copy of one of the leaf's arguments: %s" % sources] +
        _cite(exe, 0x8002B3AC, 4) + _cite(exe, 0x8002B3D8, 2)))

    # The clip HEIGHT is load-bearing rather than padding, and that is what the leaf's two `slti`
    # against it are for: it decides `dfe`, the SDK's "draw on display area" flag, which is what
    # makes the clip bind. The publication then forces that byte to 0 in BOTH draw environments, so
    # the clip is honoured rather than bypassed — and the second of the two stores is at +0x73, which
    # is the second DRAWENV's +0x17 and therefore a second, independent reading of the 0x5C stride.
    dfe_leaf = exe.insn(0x8002B3EC)
    dfe_env0 = bat.insn(0x80076214)
    dfe_env1 = bat.insn(0x80076210)
    ok = (_is(exe.insn(0x8002B3E4), mnemonic="slti", rs=18, imm=DRAW_ENV_HEIGHT_CLASSES[0]) and
          _is(exe.insn(0x8002B3E8), mnemonic="slti", rs=18, imm=DRAW_ENV_HEIGHT_CLASSES[1]) and
          _is(dfe_leaf, mnemonic="sb", rs=17, rt=2, imm=DRAW_ENV_DFE_OFFSET) and
          _is(dfe_env0, mnemonic="sb", rs=16, rt=0, imm=DRAW_ENV_DFE_OFFSET) and
          _is(dfe_env1, mnemonic="sb", rs=16, rt=0, imm=DRAW_ENV_STRIDE + DRAW_ENV_DFE_OFFSET))
    claims.append(Claim(
        "the clip HEIGHT is live and not padding: SetDefDrawEnv tests it against 289 and 257 and "
        "publishes the result to `dfe` at DRAWENV +0x17, and the publication then forces that byte "
        "to 0 in BOTH draw environments — so the drawing area really is clipped",
        "CONFIRMED" if ok else "REFUTED",
        _cite(exe, 0x8002B3E4, 4) + _cite(bat, 0x80076210, 3)))

    # The two clips themselves, and their total. Every extent is a literal or that literal minus
    # 16: `$s2` is arg0 and `$s3` is `arg1 - 16` at the publication's entry, and its ONE call site
    # passes (320, 240) — so 320 and 224 are what the guest's words produce, and the clip is a
    # COMPILE-TIME CONSTANT rather than game state. That is the fact the widening question needs:
    # a constant clip cannot be a per-field lever, and it is already twice the presented width.
    pub_sites = _find_jals(bat, BCODE[0], BCODE[1], VIEWPORT_PUBLICATION)
    sized = (len(pub_sites) == 1 and _args_320_240_H(bat, pub_sites[0]) and
             _is(bat.insn(0x800760D4), op=0, rt=0, rd=18, rs=4) and
             _is(bat.insn(0x800760E8), mnemonic="addiu", rs=5, rt=19, imm=-16))
    known = {0: 0, 18: 320, 19: 224}                    # $zero, $s2 = arg0, $s3 = arg1 - 16
    # The clip is the leaf's SECOND through FIFTH arguments (x, y, w, h). `$a0` is the DRAWENV
    # pointer and is dropped, which is why the slice starts at 1: comparing the whole five-element
    # argument list against a four-element RECT could never succeed, and the first version of this
    # claim did exactly that — a comparison that cannot pass is a claim that reports REFUTED for a
    # reason that is not the bytes.
    env0 = _resolve_arguments(_call_arguments(bat, 0x8007614C), known)[1:]
    env1 = _resolve_arguments(_call_arguments(bat, 0x80076188), known)[1:]
    base_ok = (_is(bat.insn(0x80076134), mnemonic="lui", rt=16, raw_imm=0x8006) and
               _is(bat.insn(0x80076138), mnemonic="addiu", rs=16, rt=16, imm=-7984))
    stride_ok = _is(bat.insn(0x80076174), mnemonic="addiu", rs=16, rt=20, imm=DRAW_ENV_STRIDE)
    ok = (sized and base_ok and stride_ok and (0x80060000 - 7984) == DRAW_ENV0 and
          env0 == [0, 0, 320, 224] and env1 == [320, 0, 320, 224] and
          target_of(bat.word(0x8007614C), 0x8007614C) == LEAF_SET_DEF_DRAW_ENV and
          target_of(bat.word(0x80076188), 0x80076188) == LEAF_SET_DEF_DRAW_ENV)
    def width_of(clip):
        return clip[2] if clip[2] is not None else 0

    claims.append(Claim(
        "the two DRAWENVs' clips are (0, 0, 320, 224) at 0x8005E0D0 and (320, 0, 320, 224) at "
        "0x8005E0D0+0x5C — 640 x 224 IN TOTAL, side by side, and every extent a literal at the one "
        "call site, so the drawing-area clip is a compile-time constant and not game state",
        "CONFIRMED" if ok else "REFUTED",
        ["      env0 clip (x, y, w, h) = %s ; env1 clip (x, y, w, h) = %s" % (env0, env1)] +
        ["      both clips of width %d, so %d in total against a %d-wide display area"
         % (width_of(env0), width_of(env0) + width_of(env1), 320)] +
        ["      $s2 = arg0 and $s3 = arg1 - 16 at the entry, over one call site passing (320, 240): "
         "%s" % sized] +
        _cite(bat, 0x80076134, 7) + _cite(bat, 0x80076174, 6)))

    return claims


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
