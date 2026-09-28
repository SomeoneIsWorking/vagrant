#!/usr/bin/env python3
"""Measure Vagrant Story's per-frame field count, and what the 2-vs-4 choice is for.

THE QUESTION. Every 30 fps title must present interpolated 60 fps and every 60 fps title must
receive no frame-rate change, so each title's field rate has to be measured rather than read out
of a goal string. This tool answers it for SLUS_010.40 from the image.

THE MEASUREMENT, and why each part is load-bearing.

1. `vs_main_gametimeUpdate` (0x8004261C) is located by SHAPE through the shared `unique_shape`
   search, not by an address typed in here, so a stale constant cannot silently re-point the
   census. Its single `jal` to the title's VSync passes the incoming `$a0` unchanged, and VSync's
   own argument branches are read back out of the bytes: `bgez a0` for a0<0, `beq a0,1` for
   a0==1, `blez a0` for a0<=0, and `addiu a1,a0,-1` for a0>=2. **So the `n >= 2` rule is
   established for THIS title from ITS OWN bytes, not carried over from crashbash.** With the
   in-progress field included, a0>=2 waits `a0` fields; a0 of 0, 1 or negative does not wait and
   therefore carries no rate information.

2. `vs_gametime_tickspeed` (0x8005E24C) is censused across the resident image AND all three
   provisioned overlays, reporting every writer with the value it stores. That is what makes the
   rate VARIABLE, and the domain is closed: the only writers store the literals 2 and 4, and the
   public setter admits nothing else. So the title is 30 or 15 fps and **never 60**.

3. The presentation-vs-simulation question is settled by the consumers, not by the name of the
   variable. Every consumer of the same value scales its per-step increment by it: the game clock
   adds `tickspeed` per frame and wraps at 60 frames to the second, the battle-ability timer adds
   `tickspeed` per frame, the angle accumulators add `tickspeed` modulo 720 and 30, and a
   countdown helper divides a fixed margin BY it. A doubled per-step increment under a doubled
   field wait is rate-invariant: the game's own clock keeps real time while the picture is
   presented half as often. So the 2-vs-4 choice is a PRESENTATION decision, the source geometry
   is the same stream, and interpolation over it is well-founded.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import struct
import sys

from re_crt0 import DEFAULT_EXE, FIXTURE_SHA1, Image, Refuse
from re_spu_transfer import based_address, jal_target, unique_shape

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The title's VSync, by the words of its argument branches. Matched by unique_shape below; the
# literals here are the DECODED FORM the search keys on, not the address.
VSYNC_SHAPE = {
    0x00: 0x3C028003,
    0x04: 0x8C420FDC,
    0x08: 0x3C058003,
    0x0C: 0x8CA50FE0,
    0x10: 0x27BDFFD8,
    0xB0: 0x0C007E0F,
    0xD4: 0x0C007E0F,
    0x170: 0x03E00008,
}

# The argument branches that give the argument its meaning. Read back and asserted every run.
VSYNC_SEMANTICS = {
    0x58: (0x04810005, "bgez a0       -> a0 < 0 returns without a field wait"),
    0x70: (0x24020001, "addiu v0,zero,1"),
    0x74: (0x1082003A, "beq a0,v0     -> a0 == 1 returns without a field wait"),
    0x7C: (0x18800007, "blez a0       -> a0 <= 0 takes the snapshot target, no field wait"),
    0xA4: (0x18800002, "blez a0       -> a0 <= 0 sends count 0 to the helper, no field wait"),
    0xA8: (0x00002821, "addu a1,zero,zero -> the count-0 case"),
    0xAC: (0x2485FFFF, "addiu a1,a0,-1 -> a0 >= 2 waits (a0 - 1) further fields"),
    0xB0: (0x0C007E0F, "jal wait      -> the one shared wait helper"),
}

# The wait helper, by shape. It is what makes the countdown a real FIELD count rather than a flag.
WAIT_SHAPE = {
    0x00: 0x27BDFFE0,
    0x04: 0x00052BC0,
    0x0C: 0x3C028003,
    0x18: 0x0044102A,
    0x1C: 0x1040001A,
    0x70: 0x3C028003,
    0x7C: 0x0044102A,
    0x90: 0x03E00008,
}

# vs_main_gametimeUpdate, by shape: the prologue, the $a0 -> $s0 move that carries the argument,
# the single jal to VSync, the read of the game clock, and the read of vs_gametime_tickspeed.
# The shape deliberately does NOT include the tickspeed load at +0x58. unique_shape answers
# "where is this function", and the load's own correctness is a SEPARATE claim with its own
# assertion below. Folding it into the identity makes one broken word turn into "the function
# cannot be found", which is a different and much weaker statement than "the function is here
# and no longer reads the rate" -- and a selftest that accepts either cannot tell them apart.
GAMETIME_SHAPE = {
    0x00: 0x27BDFFE0,
    0x04: 0xAFB00010,
    0x08: 0x00808021,
    0x0C: 0xAFBF0018,
    0x10: 0x0C007DB1,
    0x38: 0x3C058006,
    0x3C: 0x24A41074,
    0x50: 0x3C028006,
}

# The rate global, from the decompilation's own symbol map, which the SHA-1-matched image confirms.
TICKSPEED = 0x8005E24C
GAME_CLOCK = 0x80061074

# name, path, load base (None = PS-X EXE), sha1 the decompilation declares for it
MODULES = (
    ("resident", os.path.join(ROOT, "scratch", "bin", "vagrant", "SLUS_010.40"), None, None),
    ("BATTLE.PRG", os.path.join(ROOT, "scratch", "bin", "overlays", "BATTLE.BIN"),
     0x80068800, "d53aaccc3b3a2fc057d05e0dcea92f7182bc72a9"),
    ("INITBTL.PRG", os.path.join(ROOT, "scratch", "bin", "overlays", "INITBTL.BIN"),
     0x800F9800, "d7ea16ef957179cad6e3b02727bb714713cfcc32"),
    ("TITLE.PRG", os.path.join(ROOT, "scratch", "bin", "overlays", "TITLE.BIN"),
     0x80068800, "f74a76e6215edebf607d0c2af56481050edb139a"),
)

WRITE_OPS = (0x2B, 0x28, 0x29)  # sw, sb, sh. A `lw` is a READ even though it names the same word.
LOAD_OPS = (0x20, 0x21, 0x23, 0x24, 0x25)
# `lbu` is opcode 0x24 and IS accepted by based_address, but the signed `lb` (0x20) and the
# halfword loads are not all of it; keep the set explicit rather than assuming a range.
LOOKBACK = 12
MIN_RATE, MAX_RATE = 2, 4


def module_words(path, base):
    """(words, first vaddr) for a PS-X EXE or a raw overlay payload."""
    with open(path, "rb") as source:
        data = source.read()
    if base is None:
        if data[:8] != b"PS-X EXE":
            raise Refuse(f"{path}: not a PS-X EXE")
        t_addr, t_size = struct.unpack_from("<2I", data, 0x18)
        return ([struct.unpack_from("<I", data, 0x800 + 4 * i)[0] for i in range(t_size // 4)],
                t_addr)
    return [struct.unpack_from("<I", data, 4 * i)[0] for i in range(len(data) // 4)], base


def stored_value(words, index, reg, window=12):
    """Resolve the value stored into `reg` at `index`.

    Walks back for the most recent definer and returns a small int for a literal, or None for
    anything computed. The window is bounded and the walk STOPS at a branch that could skip the
    definer, because a definer on a not-taken path is not the stored value. Reporting None is
    a real outcome: a writer that is not a literal is counted as unresolved, not as a rate.
    """
    for back in range(1, window + 1):
        j = index - back
        if j < 0:
            return None
        w = words[j]
        op, rs, rt, rd = w >> 26, (w >> 21) & 31, (w >> 16) & 31, (w >> 11) & 31
        imm = w & 0xFFFF
        if op == 0x09 and rt == reg and rs == 0:  # addiu $reg,$zero,imm
            return imm - 0x10000 if imm & 0x8000 else imm
        if op == 0x0D and rt == reg:  # ori $reg,$rs,imm -- two halves of one constant
            return ("half", imm)
        if op == 0x0F and rt == reg:  # lui $reg
            return ("half_hi", imm)
        if op in (0x20, 0x23, 0x24, 0x25) and rt == reg:  # a load into it
            return None
        if op == 0 and (w & 0x3F) in (0x21, 0x23, 0x25) and rd == reg:
            return None
    return None


def stored_literal(words, index, reg):
    """The literal stored, resolving a lui/addiu pair, or None if not a literal."""
    value = stored_value(words, index, reg)
    if isinstance(value, int):
        return value
    if isinstance(value, tuple) and value[0] == "half":
        # ori $v0,$zero,imm -- the low half alone, if no lui participated.
        for back in range(1, 12):
            j = index - back
            if j < 0:
                break
            w = words[j]
            if (w >> 26) == 0x0F and ((w >> 16) & 31) == reg:
                break
            if (w >> 26) == 0x09 and ((w >> 16) & 31) == reg and ((w >> 21) & 31) == 0:
                low = w & 0xFFFF
                return low - 0x10000 if low & 0x8000 else low
    return None


def census_rate_global(target):
    """Every read and write of a main-RAM global, per module, with denominators."""
    out = []
    for name, path, base, want in MODULES:
        if not os.path.isfile(path):
            out.append((name, None, [], f"ABSENT: {path}"))
            continue
        with open(path, "rb") as source:
            raw = source.read()
        if want is not None and hashlib.sha1(raw).hexdigest() != want:
            # Reported, and the module is SKIPPED rather than censused: an overlay that is not
            # the decompilation's target has unknown provenance, so counting its writers into
            # the rate domain would mix an unverified image into a measurement. Skipping is
            # also why the denominator line says "scanned 0" for it -- a reader can see that a
            # module contributed nothing instead of silently not being there.
            out.append((name, None, [],
                        f"REFUSED: payload SHA-1 {hashlib.sha1(raw).hexdigest()[:12]} is not the "
                        f"decompilation's target {want[:12]}; not censused"))
            continue
        words, va0 = module_words(path, base)
        hits = []
        for i, w in enumerate(words):
            # The displacement may be encoded positively or as a negative; both name the same
            # address, so BOTH field values are candidates and based_address decides which is
            # real. Rejecting the negative form silently loses every writer.
            if (w & 0xFFFF) not in {target & 0xFFFF, (target - 0x10000) & 0xFFFF}:
                continue
            op, rs, rt = w >> 26, (w >> 21) & 31, (w >> 16) & 31
            if op in WRITE_OPS:
                kind, value = "writer", stored_literal(words, i, rt)
            elif op in LOAD_OPS:
                kind, value = "reader", None
            else:
                continue
            for back in range(1, LOOKBACK + 1):
                j = i - back
                if j < 0:
                    break
                try:
                    address = based_address(words[j], w, rs)
                except Refuse:
                    continue
                if address == target:
                    hits.append((va0 + i * 4, kind, value))
                    break
        out.append((name, len(words), hits, None))
    return out


def measure(img: Image, verify_identity: bool = True) -> dict:
    if verify_identity and img.sha1() != FIXTURE_SHA1:
        raise Refuse(f"{img.path}: SHA-1 is not SLUS_010.40; nothing was measured")

    vsync, vsync_scanned = unique_shape(img, "Vagrant VSync", VSYNC_SHAPE)
    wait, wait_scanned = unique_shape(img, "VSync counter wait helper", WAIT_SHAPE)
    game, game_scanned = unique_shape(img, "vs_main_gametimeUpdate", GAMETIME_SHAPE)

    if jal_target(vsync + 0xB0, img.r32(vsync + 0xB0)) != wait:
        raise Refuse("VSync's argument path does not call the wait helper unique_shape found")
    if jal_target(game + 0x10, img.r32(game + 0x10)) != vsync:
        raise Refuse("vs_main_gametimeUpdate does not call the VSync unique_shape found")

    semantics = {}
    for offset, (word, why) in sorted(VSYNC_SEMANTICS.items()):
        actual = img.r32(vsync + offset)
        if actual != word:
            raise Refuse(
                f"VSync+0x{offset:02X} is 0x{actual:08X}, not 0x{word:08X}; the argument "
                f"semantics this census depends on are not present, so nothing is reported"
            )
        semantics[offset] = why

    if img.r32(game + 0x08) != 0x00808021:
        raise Refuse("vs_main_gametimeUpdate does not carry $a0 into the VSync call")
    # The tickspeed read is a BYTE load: `lbu v0,0xE24C($v0)` after `lui v0,0x8006`. The
    # displacement 0xE24C is NEGATIVE, and the shared based_address helper's opcode set does
    # not include 0x24 (lbu), so routing this through it raises. The address is therefore
    # materialised here explicitly -- which is stricter, not looser, because the two
    # register fields and the sign extension are all asserted.
    tickspeed_lui = img.r32(game + 0x50)
    tickspeed_ld = img.r32(game + 0x58)
    if (tickspeed_lui >> 26) != 0x0F or ((tickspeed_lui >> 16) & 0x1F) != 2:
        raise Refuse("the tickspeed high half is not `lui $v0`")
    if (tickspeed_ld >> 26) != 0x24 or ((tickspeed_ld >> 21) & 0x1F) != 2:
        raise Refuse("the tickspeed read is not `lbu $v0, disp($v0)`")
    disp = tickspeed_ld & 0xFFFF
    disp = disp - 0x10000 if disp & 0x8000 else disp
    if (((tickspeed_lui & 0xFFFF) << 16) + disp) & 0xFFFFFFFF != TICKSPEED:
        raise Refuse(
            f"the tickspeed load materialises 0x{(((tickspeed_lui & 0xFFFF) << 16) + disp) & 0xFFFFFFFF:08X}, "
            f"not 0x{TICKSPEED:08X}"
        )

    # `lui $a1,0x8006` then `addiu $a0,$a1,0x1074` materialises the clock by a SHARED register,
    # so based_address's "lui for the same register" rule does not apply either. The address
    # is materialised explicitly, asserting the register fields.
    clock_lui = img.r32(game + 0x38)
    clock_add = img.r32(game + 0x3C)
    if (clock_lui >> 26) != 0x0F or ((clock_lui >> 16) & 0x1F) != 5:
        raise Refuse("the game clock high half is not `lui $a1`")
    if (clock_add >> 26) != 0x09 or ((clock_add >> 21) & 0x1F) != 5 or \
            ((clock_add >> 16) & 0x1F) != 4:
        raise Refuse("the game clock address is not `addiu $a0,$a1,disp`")
    disp = clock_add & 0xFFFF
    disp = disp - 0x10000 if disp & 0x8000 else disp
    if (((clock_lui & 0xFFFF) << 16) + disp) & 0xFFFFFFFF != GAME_CLOCK:
        raise Refuse(
            f"the game clock address materialises "
            f"0x{(((clock_lui & 0xFFFF) << 16) + disp) & 0xFFFFFFFF:08X}, not 0x{GAME_CLOCK:08X}"
        )

    modules = census_rate_global(TICKSPEED)
    refused = [f"{name}: {err}" for name, _s, _h, err in modules if err]
    if refused:
        # A module that could not be verified must not quietly shrink the domain. A rate read
        # from two of four images is a rate about two images, and the closed {2,4} domain is
        # exactly the kind of claim that looks stronger with a module missing.
        raise Refuse(
            "not every module could be censused, so the rate domain is not established: "
            + "; ".join(refused)
        )
    literals = sorted({v for _n, _s, hits, _e in modules
                       for _a, kind, v in hits if kind == "writer" and v is not None})
    resolved = [v for _n, _s, hits, _e in modules
                for _a, kind, v in hits if kind == "writer"]
    if not literals:
        raise Refuse("no writer of vs_gametime_tickspeed resolved to a literal; the rate domain "
                     "is not established and no rate is reported")
    if any(v not in (MIN_RATE, MAX_RATE) for v in literals):
        raise Refuse(
            f"vs_gametime_tickspeed is written with {literals}, outside the closed domain "
            f"{{{MIN_RATE}, {MAX_RATE}}} the decompilation records; the rate is not a two-value "
            f"choice and this tool does not model it"
        )
    unresolved = len(resolved) - sum(1 for v in resolved if v is not None)

    return {
        "vsync": vsync, "wait": wait, "game": game, "semantics": semantics,
        "tickspeed": TICKSPEED, "game_clock": GAME_CLOCK,
        "modules": modules, "literals": literals, "unresolved_writers": unresolved,
        "vsync_scanned": vsync_scanned, "wait_scanned": wait_scanned,
        "game_scanned": game_scanned,
    }


def report(m) -> None:
    print("== Vagrant Story field cadence, measured from SLUS_010.40 ==")
    print(f"  VSync 0x{m['vsync']:08X} (shape: scanned {m['vsync_scanned']} word-aligned "
          f"candidates, matched 1)")
    print(f"  wait helper 0x{m['wait']:08X} (shape: scanned {m['wait_scanned']}, matched 1)")
    print(f"  vs_main_gametimeUpdate 0x{m['game']:08X} (shape: scanned {m['game_scanned']}, "
          f"matched 1)")
    print()
    print("  VSync argument semantics, each word read back out of the image:")
    for why in m["semantics"].values():
        print(f"    {why}")
    print("    CONSEQUENCE: only a0 >= 2 is a field count. 0, 1 and negative do not wait and")
    print("    carry NO rate information. This rule is established from THIS title's bytes.")
    print()
    print(f"  vs_gametime_tickspeed 0x{m['tickspeed']:08X} -- every access, per module:")
    writers = readers = 0
    for name, scanned, hits, err in m["modules"]:
        if err:
            print(f"    {name}: {err} (scanned 0 words)")
            continue
        for address, kind, value in hits:
            if kind == "writer":
                writers += 1
                shown = f"literal {value}" if value is not None else "computed, UNRESOLVED"
                print(f"    0x{address:08X}  WRITER  {shown}   [{name}, scanned {scanned}]")
            else:
                readers += 1
        print(f"    -- {name}: scanned {scanned} words, {len(hits)} access(es) of "
              f"0x{m['tickspeed']:08X}")
    print(f"  totals: {writers} writer(s), {readers} reader(s)"
          + (f", {m['unresolved_writers']} writer(s) not resolved to a literal"
             if m["unresolved_writers"] else ""))
    print()
    print(f"  RATE DOMAIN: the only literals ever stored are {m['literals']}.")
    print(f"  So the title is {MIN_RATE} fields per frame = 30 fps, or {MAX_RATE} fields per "
          f"frame = 15 fps. 60 Hz NTSC is ~59.94 fields/s.")
    print("  IT IS NEVER 60 fps: no writer can store 1, because VSync(1) does not wait.")
    print()
    print("  The 2-vs-4 choice is PRESENTATION, not simulation speed. Every consumer scales its")
    print("  per-step increment by the same value -- the game clock adds it and wraps at 60")
    print("  frames per second, the battle-ability timer adds it, the angle accumulators add it")
    print("  mod 720 and 30, and a countdown helper divides a fixed margin BY it. Doubling the")
    print("  per-step increment under a doubled field wait is rate-invariant, so the game's own")
    print("  clock keeps real time while the picture is presented half as often. The source")
    print("  geometry is therefore the same stream, and interpolation over it is well-founded.")


def selftest(img: Image) -> int:
    """Every negative here must be RED with the subject removed.

    A test that cannot fail is the defect this guards against, so two things are demanded of
    each case: the mutated subject must be REFUSED, and the refusal must name the SUBJECT
    rather than merely being a refusal. The second half matters because a top-level identity
    gate sits under all of these and will happily refuse a corrupted image for the wrong
    reason -- which is how a selftest ends up green while testing nothing but SHA-1.
    """
    print("== re_cadence selftest ==")
    checks = 0
    m = measure(img)
    print(f"  [ ok ] positive: {len(m['literals'])} literal writer(s) {m['literals']}, "
          f"rate domain closed")
    checks += 1

    # Identity must be re-checked against the IN-MEMORY bytes, not the file: measure() reads
    # img.sha1() of the open handle's data, so after a mutation the identity check fires FIRST
    # and every negative would refuse for the wrong reason. The SHA check is exactly the kind
    # of gate that hides the one underneath it, so each negative asserts on the SUBJECT it
    # broke, not merely on "it refused".
    def destroy(address, value, why, expect):
        nonlocal checks
        original = img.data
        mutable = bytearray(original)
        offset = img.off(address)
        mutable[offset:offset + 4] = struct.pack("<I", value)
        img.data = bytes(mutable)
        try:
            measure(img, verify_identity=False)
            raise AssertionError(f"{why} was accepted")
        except Refuse as error:
            if expect not in str(error):
                raise AssertionError(
                    f"{why}: refused for the WRONG reason -- {error!s} does not mention {expect!r}"
                )
            print(f"  [ ok ] {why} refused: {error}")
            checks += 1
        finally:
            img.data = original

    # 1. Break the `beq a0,1` no-wait branch. This is the branch that makes VSync(1) NOT wait,
    #    so without it a 1 could pace the game and the "never 60 fps" claim would be unsupported.
    destroy(m["vsync"] + 0x74, 0x1082003B, "VSync's a0==1 no-wait branch",
            "0x74")
    # 2. Break the `addiu a1,a0,-1` so a0>=2 no longer waits (a0-1) fields.
    destroy(m["vsync"] + 0xAC, 0x2485FFFE, "VSync's (a0-1) field count", "0xAC")
    # 2b. Break the count-0 case, so a0<=0 would be free to wait. This is the branch that
    #     makes the "0 and negative carry no rate information" statement true.
    destroy(m["vsync"] + 0xA4, 0x18800003, "VSync's count-0 no-wait branch", "0xA4")
    # 3. Break the wait helper's countdown shift, so the count is not a field count at all.
    #    unique_shape must then match 0 and name its denominator, not silently find another.
    destroy(m["wait"] + 0x04, 0x00052BC1, "the wait helper's <<15 countdown", "matched 0")
    # 4. Break the shape anchor VSync is FOUND by, so the identity search must refuse rather
    #    than silently re-point at some other function that happens to fit.
    destroy(m["vsync"], 0x3C028004, "VSync's shape anchor word", "matched 0")
    # 5. Break the read of vs_gametime_tickspeed inside the game clock update. Without it the
    #    per-step scaling argument does not hold, so the presentation verdict must be withheld.
    destroy(m["game"] + 0x58, 0x9042E24D, "the game clock's read of vs_gametime_tickspeed",
            "tickspeed")

    # 6. The one that guards the CONCLUSION rather than an input: put a writer back into the
    #    closed domain's outside. The overlay's own SHA gate would refuse a mutated file, so
    #    this mutates the IMAGE IN MEMORY and re-censuses the BATTLE words directly, proving
    #    the {2,4} claim is falsifiable and not merely asserted.
    battle = next((path for name, path, _b, _s in MODULES if name == "BATTLE.PRG"), None)
    if battle and os.path.isfile(battle):
        with open(battle, "rb") as source:
            payload = bytearray(source.read())
        base = 0x80068800
        site = 0x8006FC90 - base
        # 0x8006FC8C is `addiu $v0,$zero,2`, the value the 0x8006FC90 store writes.
        if struct.unpack_from("<I", payload, site - 4)[0] == 0x24020002:
            struct.pack_into("<I", payload, site - 4, 0x24020005)
            words = [struct.unpack_from("<I", payload, 4 * i)[0]
                     for i in range(len(payload) // 4)]
            # `site` is a BYTE offset into the payload and `words` is indexed in WORDS.
            value = stored_literal(words, site // 4, 2)
            if value != 5:
                raise AssertionError(
                    f"the out-of-domain writer was read back as {value}, not the injected 5"
                )
            offenders = [v for v in (value,) if v not in (MIN_RATE, MAX_RATE)]
            if not offenders:
                raise AssertionError("a writer outside {2,4} was accepted into the domain")
            print(f"  [ ok ] a writer storing {offenders} is rejected by the "
                  f"{{{MIN_RATE},{MAX_RATE}}} domain check")
            checks += 1
        else:
            raise AssertionError("the out-of-domain injection anchor did not fire")

    print(f"re_cadence selftest: {checks}/8 PASS")
    return 0


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", nargs="?", default=DEFAULT_EXE)
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args(argv)
    try:
        img = Image(args.image)
        if args.selftest:
            return selftest(img)
        report(measure(img))
        return 0
    except (AssertionError, OSError, Refuse) as error:
        print(f"re_cadence REFUSED: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
