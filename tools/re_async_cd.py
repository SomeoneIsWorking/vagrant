#!/usr/bin/env python3
"""Measure Vagrant's asynchronous resident libds file-read contract.

This is deliberately a guest-contract instrument, not an override generator.  It derives the
read-init/poll loop, data and command callbacks, DsEndReadySystem, DsSystemStatus, the status-byte
decoder, and the libds VBlank state transition from the owned PS-EXE.  The result explains which
guest transitions a CD-controller implementation must permit: a ReadN INT1 response reports the
read bit, then the last data callback sets the disk state idle and queues Pause before a second read
can become admissible.
"""

import struct
import sys

from re_crt0 import DEFAULT_EXE, FIXTURE_SHA1, Image, Refuse
from re_spu_transfer import based_address, jal_target, materialized_address, unique_shape


def measure(img, verify_identity=True):
    if verify_identity and img.sha1() != FIXTURE_SHA1:
        raise Refuse(
            f"{img.path}: sha1 {img.sha1()} != SLUS_010.40 {FIXTURE_SHA1}; nothing was measured"
        )

    read_callback, callback_scanned = unique_shape(
        img,
        "asynchronous disk data callback",
        {
            0x00: 0x27BDFFE8,
            0x04: 0x308400FF,
            0x50: 0x24020001,
            0x54: 0x1482004B,
            0xF4: 0x8C820030,
            0xFC: 0x24420001,
            0x104: 0x0043102B,
            0x110: 0x08011044,
            0x114: 0xA0A05D10,
            0x160: 0x8C430004,
            0x168: 0x24630001,
            0x170: 0x0064182B,
        },
    )
    disk_state = based_address(
        img.r32(read_callback + 0x40), img.r32(read_callback + 0x4C), 3
    )
    idle_store = img.r32(read_callback + 0x114)
    idle_state = (idle_store >> 16) & 31
    if idle_state != 0 or based_address(img.r32(read_callback + 0xC0), idle_store, 5) != disk_state:
        raise Refuse(
            f"data callback 0x{read_callback:08X}: completion does not store zero to disk state"
        )

    end_ready = jal_target(read_callback + 0x17C, img.r32(read_callback + 0x17C))
    if jal_target(read_callback + 0x38, img.r32(read_callback + 0x38)) != end_ready:
        raise Refuse("data callback's error and final-sector paths do not share DsEndReadySystem")

    command_callback, command_scanned = unique_shape(
        img,
        "asynchronous disk command callback",
        {
            0x00: 0x27BDFFE8,
            0x04: 0x308400FF,
            0x08: 0x24020002,
            0x48: 0x3C048004,
            0x50: 0x0C009899,
            0x54: 0x2405FFFF,
            0x60: 0x3C038005,
            0x64: 0x24020004,
            0x68: 0xA0625D10,
        },
    )
    installed_data_callback = materialized_address(
        img.r32(command_callback + 0x48), img.r32(command_callback + 0x4C), 4
    )
    if installed_data_callback != read_callback:
        raise Refuse(
            f"command callback installs 0x{installed_data_callback:08X}, not measured data "
            f"callback 0x{read_callback:08X}"
        )
    start_ready = jal_target(command_callback + 0x50, img.r32(command_callback + 0x50))

    measured_end_ready, end_scanned = unique_shape(
        img,
        "DsEndReadySystem",
        {
            0x00: 0x27BDFFE8,
            0x08: 0x3C108003,
            0x14: 0x8E030000,
            0x18: 0x24020001,
            0x24: 0x8E04FFF4,
            0x30: 0x8E04FFF8,
            0x3C: 0x24040009,
            0x40: 0x00002821,
            0x44: 0x00003021,
            0x4C: 0x2407FFFF,
            0x50: 0xAE000000,
        },
    )
    if measured_end_ready != end_ready:
        raise Refuse(
            f"data callback calls 0x{end_ready:08X}, not unique DsEndReadySystem "
            f"0x{measured_end_ready:08X}"
        )
    ds_command = jal_target(end_ready + 0x48, img.r32(end_ready + 0x48))
    queue_dispatch = jal_target(ds_command + 0x214, img.r32(ds_command + 0x214))
    if jal_target(ds_command + 0x12C, img.r32(ds_command + 0x12C)) != queue_dispatch:
        raise Refuse("DsCommand's parameter and no-parameter paths do not share one dispatcher")

    system_status, status_scanned = unique_shape(
        img,
        "DsSystemStatus",
        {
            0x00: 0x27BDFFE8,
            0x04: 0x00002021,
            0x18: 0x24020001,
            0x1C: 0x16020007,
            0x2C: 0x18400003,
            0x34: 0x24100002,
            0x44: 0x03E00008,
        },
    )
    system_state_getter = jal_target(system_status + 0x0C, img.r32(system_status + 0x0C))
    queue_len_getter = jal_target(system_status + 0x24, img.r32(system_status + 0x24))
    if (
        img.r32(system_state_getter) != 0x00042080
        or img.r32(system_state_getter + 0x04) != 0x3C028003
        or img.r32(system_state_getter + 0x08) != 0x00441021
    ):
        raise Refuse("DsSystemStatus state getter is not the measured indexed libds state load")
    system_state = based_address(
        img.r32(system_state_getter + 0x04),
        img.r32(system_state_getter + 0x0C),
        2,
    )
    if img.r32(queue_len_getter) != 0x3C028004:
        raise Refuse("DsSystemStatus queue-length getter has an unexpected base")
    queue_len = based_address(
        img.r32(queue_len_getter), img.r32(queue_len_getter + 0x04), 2
    )

    command_sync, sync_scanned = unique_shape(
        img,
        "libds controller-status state machine",
        {
            0x00: 0x27BDFFE8,
            0x08: 0x00A08021,
            0x0C: 0x3C058003,
            0x10: 0x24A526A0,
            0x18: 0x8CA20000,
            0x1C: 0x2403000C,
            0x34: 0x24060002,
            0x180: 0x2C420002,
            0x19C: 0x90A2FFF4,
            0x1A4: 0x30420002,
            0x1A8: 0x14400033,
            0x1B8: 0x24020001,
            0x1BC: 0xACA2FFFC,
            0x1C0: 0x2402000B,
        },
    )
    command_state = materialized_address(
        img.r32(command_sync + 0x0C), img.r32(command_sync + 0x10), 5
    )
    controller_status = command_state - 12
    if command_state != system_state + 4:
        raise Refuse(
            f"libds command state 0x{command_state:08X} is not adjacent to system state "
            f"0x{system_state:08X}"
        )

    status_decoder, decoder_scanned = unique_shape(
        img,
        "libds response-status decoder",
        {
            0x00: 0x27BDFFE8,
            0x08: 0x308400FF,
            0x0C: 0x24020005,
            0x58: 0x3C048003,
            0x5C: 0x248426B0,
            0x64: 0x000311C2,
            0x68: 0xA0820000,
            0x6C: 0x00031182,
            0x70: 0x30420001,
            0x74: 0xA0820001,
            0x78: 0x00031142,
            0x7C: 0x30420001,
            0x84: 0x30630001,
            0x88: 0xA0820002,
            0x8C: 0xA0830003,
            0x90: 0xA085FFE4,
        },
    )
    decoded_status = materialized_address(
        img.r32(status_decoder + 0x58), img.r32(status_decoder + 0x5C), 4
    )
    decoded_read = decoded_status + 2
    if decoded_status - 28 != controller_status:
        raise Refuse(
            f"status decoder raw byte 0x{decoded_status - 28:08X} is not controller status "
            f"0x{controller_status:08X}"
        )

    status_tick, tick_scanned = unique_shape(
        img,
        "libds VBlank read-active transition",
        {
            0x00: 0x27BDFFE0,
            0x04: 0x3C038003,
            0x08: 0x246326C0,
            0x6C: 0x8C83FFE0,
            0x70: 0x24100001,
            0x78: 0x24020002,
            0x1C8: 0x24020011,
            0x1E4: 0x14620011,
            0x1EC: 0x9082FFF6,
            0x1F4: 0x10400004,
            0x1FC: 0xAC90FFE0,
            0x204: 0xAC85FFE4,
        },
    )
    tick_base = materialized_address(
        img.r32(status_tick + 0x3C), img.r32(status_tick + 0x40), 4
    )
    if (
        tick_base - 32 != system_state
        or tick_base - 28 != command_state
        or tick_base - 10 != decoded_read
    ):
        raise Refuse(
            "VBlank ReadN transition does not join the measured system state, command state, "
            "and decoded read-status byte"
        )

    disk_init, init_scanned = unique_shape(
        img,
        "resident disk read initializer",
        {
            0x00: 0x27BDFFE8,
            0x04: 0x00A03821,
            0x20: 0x00071AC2,
            0x24: 0x30E207FF,
            0x50: 0x10400003,
            0x58: 0x24620001,
            0x68: 0x24020005,
            0x70: 0x080110EF,
            0x74: 0x24020001,
        },
    )
    init_state = based_address(img.r32(disk_init + 0x0C), img.r32(disk_init + 0x6C), 16)
    if init_state != disk_state:
        raise Refuse(
            f"disk initializer writes 0x{init_state:08X}, not callback state 0x{disk_state:08X}"
        )

    disk_load, load_scanned = unique_shape(
        img,
        "blocking resident file-read poll loop",
        {
            0x00: 0x27BDFFD8,
            0x18: 0x0C0110D0,
            0x2C: 0x24130002,
            0x30: 0x24120003,
            0x34: 0x24110005,
            0x38: 0x0C0110C4,
            0x48: 0x0C0110C4,
            0x58: 0x0C0110C4,
            0x68: 0x0C0110C4,
            0x78: 0x0C010987,
            0x7C: 0x00002021,
            0x80: 0x0801125D,
        },
    )
    if jal_target(disk_load + 0x18, img.r32(disk_load + 0x18)) != disk_init:
        raise Refuse("resident file-read loop does not call the measured initializer")
    get_state = jal_target(disk_load + 0x38, img.r32(disk_load + 0x38))
    if any(
        jal_target(disk_load + off, img.r32(disk_load + off)) != get_state
        for off in (0x48, 0x58, 0x68)
    ):
        raise Refuse("resident file-read loop's four state probes do not share one getter")

    return {
        "disk_load": disk_load,
        "disk_init": disk_init,
        "disk_state": disk_state,
        "command_callback": command_callback,
        "read_callback": read_callback,
        "start_ready": start_ready,
        "end_ready": end_ready,
        "ds_command": ds_command,
        "queue_dispatch": queue_dispatch,
        "system_status": system_status,
        "system_state": system_state,
        "queue_len": queue_len,
        "command_sync": command_sync,
        "command_state": command_state,
        "controller_status": controller_status,
        "status_decoder": status_decoder,
        "decoded_read": decoded_read,
        "status_tick": status_tick,
        "scanned": callback_scanned
        + command_scanned
        + end_scanned
        + status_scanned
        + sync_scanned
        + decoder_scanned
        + tick_scanned
        + init_scanned
        + load_scanned,
    }


def selftest(img, measured):
    print("== re_async_cd selftest ==")
    original = img.data
    checks = 0
    for label, va, expected in (
        ("destroyed data-callback completion", measured["read_callback"] + 0x114, "matched 0"),
        ("changed DsEndReadySystem Pause", measured["end_ready"] + 0x3C, "matched 0"),
        ("destroyed libds Ready value", measured["status_tick"] + 0x70, "matched 0"),
        ("destroyed libds ReadN-active predicate", measured["status_tick"] + 0x1EC, "matched 0"),
    ):
        mutated = bytearray(original)
        mutated[img.off(va) : img.off(va) + 4] = struct.pack("<I", 0)
        img.data = bytes(mutated)
        try:
            measure(img, verify_identity=False)
            raise AssertionError(f"{label} was accepted")
        except Refuse as error:
            if expected not in str(error) or "scanned" not in str(error):
                raise AssertionError(f"{label} lacked a searched denominator: {error}")
            print(f"  [ ok ] {label} refused: {error}")
            checks += 1
        finally:
            img.data = original
    print(f"re_async_cd selftest: {checks}/4 PASS")


def main(argv):
    args = list(argv)
    do_selftest = "--selftest" in args
    args = [arg for arg in args if arg != "--selftest"]
    if len(args) > 1:
        print("usage: re_async_cd.py [--selftest] [SLUS_010.40]", file=sys.stderr)
        return 2
    try:
        img = Image(args[0] if args else DEFAULT_EXE)
        measured = measure(img)
        print("== Vagrant asynchronous resident libds read contract ==")
        print(
            f"  file poll 0x{measured['disk_load']:08X} -> init 0x{measured['disk_init']:08X}; "
            f"disk state 0x{measured['disk_state']:08X}"
        )
        print(
            f"  command callback 0x{measured['command_callback']:08X} installs data callback "
            f"0x{measured['read_callback']:08X}"
        )
        print(
            f"  final data callback -> DsEndReadySystem 0x{measured['end_ready']:08X} -> "
            f"DsCommand 0x{measured['ds_command']:08X}(Pause=9)"
        )
        print(
            f"  DsSystemStatus 0x{measured['system_status']:08X}: libds state "
            f"0x{measured['system_state']:08X}, command queue length "
            f"0x{measured['queue_len']:08X}"
        )
        print(
            f"  controller sync 0x{measured['command_sync']:08X}: command state "
            f"0x{measured['command_state']:08X}, response status "
            f"0x{measured['controller_status']:08X}; queue dispatcher "
            f"0x{measured['queue_dispatch']:08X}"
        )
        print(
            f"  status decoder 0x{measured['status_decoder']:08X}: Read bit -> "
            f"0x{measured['decoded_read']:08X}; VBlank transition "
            f"0x{measured['status_tick']:08X} changes ReadN 0x11/Busy to idle only when set"
        )
        print(f"  searched {measured['scanned']} word-aligned shape candidates")
        print(
            "  required order: ReadN INT1 reports CdlStatRead; guest VBlank marks libds idle; "
            "the final data callback then queues a dispatchable Pause"
        )
        if do_selftest:
            selftest(img, measured)
        return 0
    except (AssertionError, OSError, Refuse) as error:
        print(f"re_async_cd REFUSED: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
