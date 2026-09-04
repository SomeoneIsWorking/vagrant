#!/usr/bin/env python3
"""Measure Vagrant's boot-time SPU DMA completion route from the owned PS-EXE.

The game waits on a guest flag after SpuWrite. Sony's SPU library registers its completion on DMA
channel 4, and libapi's low-level callback owner stores handlers in an eight-word table. This
instrument derives that table and the complete StartSound -> writer -> waiter/callback chain from
executable bytes, then checks the title's typed fact used by the future dynarec adapter.

Every search is uniqueness-gated. The selftest destroys one executable shape and shifts the shipped
table by four bytes, proving that the instrument can report both answers.
"""
import os
import re
import struct
import sys

from re_crt0 import DEFAULT_EXE, FIXTURE_SHA1, Image, Refuse, s16

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FACTS = os.path.join(ROOT, "game", "core", "resident_facts.h")


def words(img):
    for va in range(img.lo, img.hi, 4):
        yield va, img.r32(va)


def unique_shape(img, name, shape):
    matches = []
    scanned = 0
    for va, _ in words(img):
        if va + max(shape) + 4 > img.hi:
            break
        scanned += 1
        if all(img.r32(va + off) == word for off, word in shape.items()):
            matches.append(va)
    if len(matches) != 1:
        shown = ", ".join(f"0x{x:08X}" for x in matches[:8]) or "none"
        raise Refuse(
            f"{name}: scanned {scanned} word-aligned candidates, matched {len(matches)} "
            f"({shown}); cannot identify a unique owner"
        )
    return matches[0], scanned


def jal_target(pc, word):
    if word >> 26 != 3:
        raise Refuse(f"expected jal at 0x{pc:08X}, found 0x{word:08X}")
    return ((pc + 4) & 0xF0000000) | ((word & 0x03FFFFFF) << 2)


def materialized_address(hi_word, lo_word, reg):
    if hi_word >> 26 != 0x0F or (hi_word >> 16) & 31 != reg:
        raise Refuse(f"expected lui for register {reg}, found 0x{hi_word:08X}")
    if lo_word >> 26 not in (0x08, 0x09) or (lo_word >> 21) & 31 != reg or (lo_word >> 16) & 31 != reg:
        raise Refuse(f"expected addi/addiu for register {reg}, found 0x{lo_word:08X}")
    return (((hi_word & 0xFFFF) << 16) + s16(lo_word & 0xFFFF)) & 0xFFFFFFFF


def based_address(hi_word, memory_word, reg):
    if hi_word >> 26 != 0x0F or (hi_word >> 16) & 31 != reg:
        raise Refuse(f"expected lui for register {reg}, found 0x{hi_word:08X}")
    if (memory_word >> 21) & 31 != reg or memory_word >> 26 not in (0x20, 0x21, 0x23, 0x28, 0x29, 0x2B):
        raise Refuse(f"expected memory operand based on register {reg}, found 0x{memory_word:08X}")
    return (((hi_word & 0xFFFF) << 16) + s16(memory_word & 0xFFFF)) & 0xFFFFFFFF


def measure(img, verify_identity=True):
    if verify_identity and img.sha1() != FIXTURE_SHA1:
        raise Refuse(
            f"{img.path}: sha1 {img.sha1()} != SLUS_010.40 {FIXTURE_SHA1}; nothing was measured"
        )

    # The active low-level libapi DMA owner preserves channel in a2, materialises the handler table,
    # indexes it by channel*4, and has both install and clear stores to that slot. Another callback
    # table exists in this executable, so this ownership shape and the startup-vector proof below
    # are both required; merely finding an indexed callback table is not enough.
    dma_owner, dma_scanned = unique_shape(
        img,
        "low-level DMA callback owner",
        {
            0x00: 0x00803021,
            0x0C: 0x00061080,
            0x10: 0x00431821,
            0x14: 0x8C670000,
            0x18: 0x00A02021,
            0x38: 0xAC640000,
            0x74: 0xAC600000,
            0xA4: 0x03E00008,
        },
    )
    dma_table = materialized_address(img.r32(dma_owner + 0x04), img.r32(dma_owner + 0x08), 3)

    # startIntrDMA clears eight handlers and returns this exact owner. Callback-system bootstrap then
    # stores that return into descriptor slot +4, which is the slot the public DMACallback wrapper
    # indirect-calls. This disambiguates the active DMA table from the other indexed callback table.
    dma_start, start_dma_scanned = unique_shape(
        img,
        "DMA callback-system initializer",
        {
            0x00: 0x27BDFFE8,
            0x0C: 0xAFBF0010,
            0x14: 0x24050008,
            0x3C: 0x8FBF0010,
            0x40: 0x27BD0018,
            0x44: 0x03E00008,
        },
    )
    if materialized_address(img.r32(dma_start + 0x04), img.r32(dma_start + 0x08), 4) != dma_table:
        raise Refuse("DMA initializer does not clear the measured callback table")
    returned_owner = materialized_address(img.r32(dma_start + 0x34), img.r32(dma_start + 0x38), 2)
    if returned_owner != dma_owner:
        raise Refuse(
            f"DMA initializer returns 0x{returned_owner:08X}, not measured owner 0x{dma_owner:08X}"
        )

    # Sony libspu's adapter is the unique tiny wrapper that forwards its callback in a1 and fixes
    # a0 to DMA channel 4. This ties the boot wait to the table's channel-4 slot.
    spu_dma_adapter, adapter_scanned = unique_shape(
        img,
        "SPU DMA callback adapter",
        {
            0x00: 0x27BDFFE8,
            0x04: 0xAFBF0010,
            0x08: 0x00802821,
            0x10: 0x24040004,
            0x14: 0x8FBF0010,
            0x18: 0x27BD0018,
            0x1C: 0x03E00008,
        },
    )
    dma_callback_api = jal_target(spu_dma_adapter + 0x0C, img.r32(spu_dma_adapter + 0x0C))
    callback_vector = based_address(img.r32(dma_callback_api), img.r32(dma_callback_api + 0x04), 2)
    if img.r32(dma_callback_api + 0x10) != 0x8C420004:
        raise Refuse("public DMACallback wrapper does not indirect through descriptor slot +4")

    vector_bootstrap = []
    for va, _ in words(img):
        if va + 0x10 >= img.hi or img.r32(va) >> 26 != 3:
            continue
        if jal_target(va, img.r32(va)) != dma_start:
            continue
        if based_address(img.r32(va + 0x08), img.r32(va + 0x0C), 4) != callback_vector:
            continue
        if img.r32(va + 0x14) != 0xAC820004:
            continue
        vector_bootstrap.append(va)
    if len(vector_bootstrap) != 1:
        shown = ", ".join(f"0x{x:08X}" for x in vector_bootstrap) or "none"
        raise Refuse(
            f"DMA vector bootstrap: scanned {img.t_size // 4} word-aligned candidates, matched "
            f"{len(vector_bootstrap)} ({shown})"
        )

    # The game writer sets one state word to 1, installs a materialised callback, then calls the SPU
    # transfer routine. The state word and callback are derived, not supplied as search anchors.
    writer, writer_scanned = unique_shape(
        img,
        "game SPU writer",
        {
            0x00: 0x27BDFFE0,
            0x04: 0xAFB00010,
            0x08: 0x00808021,
            0x0C: 0xAFB10014,
            0x10: 0x00A08821,
            0x18: 0x24020001,
            0x24: 0xAC620000 | 0x77F0,
            0x30: 0x02002021,
            0x38: 0x02202821,
            0x48: 0x03E00008,
        },
    )
    state_word = based_address(img.r32(writer + 0x14), img.r32(writer + 0x24), 3)
    completion = materialized_address(img.r32(writer + 0x1C), img.r32(writer + 0x2C), 4)
    transfer_callback_api = jal_target(writer + 0x28, img.r32(writer + 0x28))
    spu_write = jal_target(writer + 0x34, img.r32(writer + 0x34))

    callback, callback_scanned = unique_shape(
        img,
        "SPU completion callback",
        {
            0x00: 0x27BDFFE8,
            0x04: 0xAFBF0010,
            0x0C: 0x00002021,
            0x10: 0x8FBF0010,
            0x18: 0xAC400000 | (state_word & 0xFFFF),
            0x1C: 0x03E00008,
        },
    )
    if callback != completion:
        raise Refuse(
            f"writer materialises callback 0x{completion:08X}, but unique state-clear callback is "
            f"0x{callback:08X}"
        )
    if jal_target(callback + 0x08, img.r32(callback + 0x08)) != transfer_callback_api:
        raise Refuse("completion callback does not unregister through the writer's callback API")

    waiter, waiter_scanned = unique_shape(
        img,
        "SPU transfer waiter",
        {
            0x04: 0x8C830000 | (state_word & 0xFFFF),
            0x08: 0x24020001,
            0x0C: 0x14620005,
            0x14: 0x8C820000 | (state_word & 0xFFFF),
            0x1C: 0x1043FFFD,
            0x24: 0x03E00008,
        },
    )
    if based_address(img.r32(waiter), img.r32(waiter + 0x04), 4) != state_word:
        raise Refuse("waiter and writer do not materialise the same state-word page")

    # StartSound is found by its concrete transfer setup: mode 0, start 0x1010, 64-byte write, then
    # the two measured calls in order. It establishes that this route is a boot prerequisite.
    start_sound, start_scanned = unique_shape(
        img,
        "StartSound transfer sequence",
        {
            0x2C: 0x00002021,
            0x34: 0x24041010,
            0x44: 0x24050040,
            0x4C: 0x00000000,
        },
    )
    if jal_target(start_sound + 0x40, img.r32(start_sound + 0x40)) != writer:
        raise Refuse("StartSound's 64-byte transfer does not call the measured writer")
    if jal_target(start_sound + 0x48, img.r32(start_sound + 0x48)) != waiter:
        raise Refuse("StartSound does not immediately call the measured transfer waiter")

    return {
        "dma_owner": dma_owner,
        "dma_table": dma_table,
        "dma_callback_api": dma_callback_api,
        "dma_start": dma_start,
        "callback_vector": callback_vector,
        "vector_bootstrap": vector_bootstrap[0],
        "spu_dma_adapter": spu_dma_adapter,
        "writer": writer,
        "waiter": waiter,
        "completion": completion,
        "transfer_callback_api": transfer_callback_api,
        "spu_write": spu_write,
        "state_word": state_word,
        "start_sound": start_sound,
        "dma_scanned": dma_scanned,
        "start_dma_scanned": start_dma_scanned,
        "adapter_scanned": adapter_scanned,
        "writer_scanned": writer_scanned,
        "callback_scanned": callback_scanned,
        "waiter_scanned": waiter_scanned,
        "start_scanned": start_scanned,
    }


def check_source(measured, text):
    match = re.search(r"\bkDmaCallbackTable\s*=\s*(0x[0-9A-Fa-f]+)", text)
    if not match:
        raise Refuse(f"{FACTS}: did not find kDmaCallbackTable")
    shipped = int(match.group(1), 0)
    ok = shipped == measured["dma_table"]
    print(
        f"  [{'ok' if ok else 'FAIL':>4}] dmaCallbackTable shipped=0x{shipped:08X} "
        f"measured=0x{measured['dma_table']:08X}"
    )
    if shipped != measured["dma_table"]:
        raise Refuse("shipping mismatch: dmaCallbackTable")


def selftest(img, measured):
    print("== re_spu_transfer selftest ==")
    checks = 0
    with open(FACTS, encoding="utf-8") as config_file:
        text = config_file.read()
    check_source(measured, text)
    checks += 1

    original = img.data
    mutable = bytearray(original)
    off = img.off(measured["spu_dma_adapter"] + 0x10)
    mutable[off : off + 4] = struct.pack("<I", 0)
    img.data = bytes(mutable)
    try:
        measure(img, verify_identity=False)
        raise AssertionError("destroyed SPU DMA adapter was accepted")
    except Refuse as error:
        if "scanned" not in str(error) or "matched 0" not in str(error):
            raise AssertionError(f"negative lacked denominator: {error}")
        print(f"  [ ok ] destroyed SPU DMA adapter refused: {error}")
        checks += 1
    finally:
        img.data = original

    old = f"kDmaCallbackTable = 0x{measured['dma_table']:08X}"
    changed = text.replace(old, f"kDmaCallbackTable = 0x{measured['dma_table'] + 4:08X}", 1)
    if changed == text:
        raise AssertionError("shipping mutation anchor did not fire")
    try:
        check_source(measured, changed)
        raise AssertionError("+4 shipping table was accepted")
    except Refuse as error:
        if "dmaCallbackTable" not in str(error):
            raise AssertionError(f"shipping negative did not name field: {error}")
        print(f"  [ ok ] +4 shipping DMA table refused: {error}")
        checks += 1
    print(f"re_spu_transfer selftest: {checks}/3 PASS")


def main(argv):
    args = list(argv)
    do_check = "--check-source" in args
    do_selftest = "--selftest" in args
    args = [arg for arg in args if arg not in ("--check-source", "--selftest")]
    if len(args) > 1:
        print("usage: re_spu_transfer.py [--check-source] [--selftest] [SLUS_010.40]", file=sys.stderr)
        return 2
    try:
        img = Image(args[0] if args else DEFAULT_EXE)
        measured = measure(img)
        print("== Vagrant boot SPU transfer-completion route ==")
        print(
            f"  StartSound 0x{measured['start_sound']:08X} -> writer 0x{measured['writer']:08X} "
            f"-> waiter 0x{measured['waiter']:08X}"
        )
        print(
            f"  state 0x{measured['state_word']:08X}; completion 0x{measured['completion']:08X}; "
            f"SpuWrite 0x{measured['spu_write']:08X}"
        )
        print(
            f"  SPU adapter 0x{measured['spu_dma_adapter']:08X} registers DMA channel 4 through "
            f"0x{measured['dma_callback_api']:08X}"
        )
        print(
            f"  low-level DMA owner 0x{measured['dma_owner']:08X} -> table "
            f"0x{measured['dma_table']:08X} ({measured['dma_scanned']} candidates scanned)"
        )
        print("  boundary: psxport owns DMA4 completion; the guest callback body and wait flag stay guest-owned")
        if do_check:
            with open(FACTS, encoding="utf-8") as config_file:
                check_source(measured, config_file.read())
        if do_selftest:
            selftest(img, measured)
        return 0
    except (AssertionError, OSError, Refuse) as error:
        print(f"re_spu_transfer REFUSED: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
