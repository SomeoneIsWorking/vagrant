#!/usr/bin/env python3
"""re_overlay.py — MEASURE the load base of every .PRG overlay module in SLUS_010.40 (RE-03).

  python3 tools/re_overlay.py [/path/to/disc.chd]   # the full measurement, with citations
  python3 tools/re_overlay.py --check-config        # diff the SHIPPING config/seeds against the bytes
  python3 tools/re_overlay.py --selftest            # prove every gate here can print the OTHER answer

WHY THIS EXISTS. An overlay is keyed BY its load address: a wrong base emits a whole module of
correctly-decoded instructions at WRONG addresses, and every `jal` target, pointer test and router
lookup is then silently wrong — it does not fail cleanly, it reads as a framework bug. rood-reverse's
splat configs STATE a `vram:` per module. That is a hypothesis about a different build pipeline, not
evidence about this port, so nothing here reads those configs. Everything below is derived from our
own extracted bytes plus our own disc's ISO directory.

THREE METHODS. They do not share an implementation; M2 and M3 share the owned image only through
M3's explicit SHA-1 identity gate.

  M1 LOADER (resident-code corroboration).
      The resident executable holds a table of overlay destination addresses. This tool does not
      assume where: it finds every `lui rX,hi / lw rD,K(rX)` whose effective address lands inside the
      resident image and reads that word out of the executable. It reports EVERY candidate; a site is
      resolved to a file only if the following `jal` also carries a (lba, byteCount) descriptor — in
      a stack struct, in argument registers, or loaded from an indexed table — that matches a REAL
      FILE on this disc by LBA, with a whole-sector byte count covering that file. A site that fails
      the disc match is UNRESOLVED, never quietly dropped: the disc is the referee.
      So M1's output is (file on the disc) -> (address the loader writes it to), with a disassembly
      citation for each, and the ISO directory as an independent witness for every descriptor.

  M2 SELF-CONSISTENCY (the measurement; needs no loader and no reference config).
      MIPS `jal` encodes an ABSOLUTE target (low 28 bits), so a module's own jal targets are fixed
      numbers, independent of where the module loads. Its function ENTRY offsets are also fixed
      (`addiu $sp,$sp,-N` at file offset O). The load base is therefore the value B that makes the
      most jal targets land exactly on an entry: for every (target T, entry offset O) pair, B = T - O,
      and the true base is the mode of that histogram. Wrong by even 4 and almost every coincidence
      is destroyed. M2's ground truth is checkable: run it on SLUS_010.40 itself and it must recover
      that file's own PS-EXE `t_addr - 0x800` (the 2 KiB header), a number this method never sees.

  M3 REFERENCE IDENTITY + LINK ADDRESS (independent corroboration).
      For each non-empty .PRG, the tool parses rood-reverse's `sha1`, `basename`, and segment `vram`
      from that module's splat config. It first hashes OUR extracted file and requires the stated
      `sha1`; only then does it compare M2's measured base with `vram`. Thus the reference address is
      never applied to an unproven image, and it is never the source of M2's answer. All 20 non-empty
      modules must have both an identity match and an address agreement before RE-03 can pass.

WHAT A NEGATIVE PRINTS. Every run prints its denominators: code images on the disc, images extracted,
slot-read sites scanned, sites resolved, sites the descriptor could NOT be recovered for (with their
addresses), modules M2 could not decide (with the histogram margin), and the modules M1 and M2
DISAGREE about. The tool REFUSES (exit 2) when the disc, the executable or the modules are missing —
a search of a corpus that is not there must never look like a clean pass. A module with a thin M2
margin is printed as THIN with its numbers rather than silently averaged into a pass.

Exit: 0 measured and consistent · 1 a gate FAILED or methods disagree · 2 could not look.
"""
import argparse
import collections
import hashlib
import os
import re
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import discdump  # noqa: E402
import re_crt0  # noqa: E402  (disasm1 — one disassembler in this repo, not two)
from resolve_disc import resolve  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXE_ON_DISC = "SLUS_010.40"
PRG_DIR = os.path.join(ROOT, "scratch", "raw", "prg")
CONFIG_SRC = os.path.join(ROOT, "game", "core", "game_config.cpp")
SEEDS_SRC = os.path.join(ROOT, "game", "recomp_seeds.json")
ROOD_CONFIG = os.path.join(ROOT, "external", "rood-reverse", "config")

SECTOR = 2048
EXE_HEADER = 0x800          # a PS-EXE's 2 KiB header; .PRG files have NO header (measured: M2 on
                            # every module recovers a base at file offset 0, the exe at 0x800)
ARG_REGS = (4, 5, 6, 7)     # a0..a3


class Refuse(Exception):
    """The tool could not look. Never a measurement, never a pass."""


# ---------------------------------------------------------------------------- images and the disc --

def pad2k(n):
    return (n + SECTOR - 1) // SECTOR * SECTOR


class Img:
    """One extracted image: its bytes as words, plus wherever we have measured it to load."""

    def __init__(self, name, data):
        self.name = name
        self.data = data
        n = len(data) // 4
        self.w = struct.unpack("<%dI" % n, data[:n * 4]) if n else ()
        self.base = None          # M2's answer; filled by sweep()
        self.m2 = None            # (best, hits, second)

    @property
    def stem(self):
        return os.path.splitext(os.path.basename(self.name))[0]

    def va(self, off):
        return None if self.base is None else (self.base + off) & 0xFFFFFFFF

    def off_of(self, va):
        if self.base is None:
            return None
        o = (va - self.base) & 0xFFFFFFFF
        return o if o < len(self.data) else None


def code_images(disc):
    """Every code image on the disc: the boot exe plus every *.PRG. Refuses an empty corpus."""
    files = discdump.listing(disc)
    out = [(p, l, s) for p, l, s in files if p == EXE_ON_DISC or p.upper().endswith(".PRG")]
    if not out:
        raise Refuse(f"{disc} lists {len(files)} files and NONE of them is {EXE_ON_DISC} or a .PRG — "
                     "this is not the disc this tool measures")
    return files, out


def extract_all(disc, images):
    """Extract each code image into scratch/raw/prg. Returns {basename: Img} + a failure list."""
    os.makedirs(PRG_DIR, exist_ok=True)
    got, failed, empty = {}, [], []
    for path, _lba, size in images:
        if size == 0:
            # A real, measured answer, not an omission: MENU/MENUA.PRG is 0 bytes on this disc, so
            # there is no code to place and no base to measure. Reported, never counted as measured.
            empty.append(path)
            continue
        dest = os.path.join(PRG_DIR, os.path.basename(path))
        if not (os.path.isfile(dest) and os.path.getsize(dest) == size):
            if not discdump.get(disc, path, PRG_DIR):
                failed.append(path)
                continue
        got[os.path.basename(path)] = Img(path, open(dest, "rb").read())
    return got, failed, empty


def psexe(data):
    if data[:8] != b"PS-X EXE":
        raise Refuse("the extracted boot image is not a PS-X EXE — refusing to measure it")
    f = struct.unpack("<11I", data[0x10:0x10 + 44])
    return dict(zip(["pc0", "gp0", "t_addr", "t_size", "d_addr", "d_size",
                     "b_addr", "b_size", "s_addr", "s_size", "sp_gp"], f))


def reference_records(root=ROOD_CONFIG):
    """Parse the minimum splat-config fields that identify and place each .PRG.

    This is intentionally a strict, dependency-free parser for three scalar keys, not a permissive
    YAML implementation. Missing/duplicate fields refuse the corpus instead of quietly reducing the
    denominator. The first `vram` belongs to the module's sole top-level segment in every PRG config;
    configs with zero or multiple distinct `vram` values refuse because that shape is not understood.
    """
    if not os.path.isdir(root):
        raise Refuse(f"rood-reverse config directory is missing: {root}")
    configs = []
    for parent, _dirs, names in os.walk(root):
        if "splat.yaml" in names and parent.upper().endswith(".PRG"):
            configs.append(os.path.join(parent, "splat.yaml"))
    if not configs:
        raise Refuse(f"scanned {root} and found 0 .PRG/splat.yaml configs")

    records = {}
    scalar = re.compile(r"^\s*(sha1|basename|vram):\s*([^#\s]+)")
    for path in sorted(configs):
        vals = collections.defaultdict(list)
        for line in open(path, encoding="utf-8"):
            m = scalar.match(line)
            if m:
                vals[m.group(1)].append(m.group(2))
        sha = vals["sha1"]
        names = vals["basename"]
        vrams = sorted(set(vals["vram"]))
        if len(sha) != 1 or len(names) != 1 or len(vrams) != 1:
            raise Refuse(f"{path} must contain exactly one sha1, one basename, and one distinct "
                         f"vram; got sha1={sha}, basename={names}, vram={vrams}")
        name = names[0].replace("\\", "/").upper()
        if name in records:
            raise Refuse(f"duplicate rood-reverse config for {name}: {records[name]['config']} and "
                         f"{path}")
        if not re.fullmatch(r"[0-9a-fA-F]{40}", sha[0]):
            raise Refuse(f"{path} has malformed sha1 {sha[0]!r}")
        try:
            base = int(vrams[0], 0)
        except ValueError:
            raise Refuse(f"{path} has malformed vram {vrams[0]!r}")
        records[name] = {"sha1": sha[0].lower(), "base": base, "config": path}
    return records


def reference_verdict(img, rec):
    """Run the shipping M3 gate for one image: identity first, address only after identity."""
    digest = hashlib.sha1(img.data).hexdigest()
    if digest != rec["sha1"]:
        return "sha", digest
    if img.base is None:
        return "no-m2", digest
    if img.base != rec["base"]:
        return "base", digest
    return "ok", digest


# ------------------------------------------------------- M2: base from the module's own bytes only --

def entry_offsets(w):
    """File offsets of `addiu $sp,$sp,-N` — a non-leaf function's first instruction."""
    return [i * 4 for i, x in enumerate(w) if (x >> 16) == 0x27BD and (x & 0x8000)]


def jal_targets(w):
    """The ABSOLUTE targets of every `jal`. Base-independent: bits 27..2 come from the encoding."""
    return {0x80000000 | ((x & 0x03FFFFFF) << 2) for x in w if (x >> 26) == 3}


def sweep(img):
    """Histogram of (jal target - entry offset). Returns (best, hits, second_hits, n_entry, n_tgt)."""
    ent, tgt = entry_offsets(img.w), jal_targets(img.w)
    h = collections.Counter()
    for t in tgt:
        for o in ent:
            h[(t - o) & 0xFFFFFFFF] += 1
    if not h:
        return None, 0, 0, len(ent), len(tgt)
    top = h.most_common(2)
    best, hits = top[0]
    second = top[1][1] if len(top) > 1 else 0
    # A base must place the module in KSEG0 RAM and leave the whole image inside the 2 MB of it.
    if not (0x80000000 <= best <= 0x801FFFFF and best + len(img.data) <= 0x80200000):
        return None, hits, second, len(ent), len(tgt)
    return best, hits, second, len(ent), len(tgt)


M2_MIN_HITS = 2       # below this there is no mode, only noise
M2_MIN_RATIO = 2.0    # best must beat the runner-up by this much to be more than a coin flip
M2_THIN_RATIO = 4.0   # between MIN and THIN the answer stands but is printed as THIN


# ------------------------------------------------------------ M1: the loader, refereed by the disc --

class Fld:
    """A symbolic field of a word loaded from a constant table: ((w >> shr) & mask) << shl.

    The shifts and the mask are READ OFF the instructions between the table load and the store of
    the argument — the packed layout is never assumed. Anything outside this shape stays unresolved.
    """

    __slots__ = ("key", "shr", "mask", "shl")

    def __init__(self, key, shr=0, mask=None, shl=0):
        self.key, self.shr, self.mask, self.shl = key, shr, mask, shl

    def with_(self, **kw):
        f = Fld(self.key, self.shr, self.mask, self.shl)
        for k, v in kw.items():
            setattr(f, k, v)
        return f

    def of(self, word):
        v = word >> self.shr
        if self.mask is not None:
            v &= self.mask
        return (v << self.shl) & 0xFFFFFFFF

    def __repr__(self):
        m = "" if self.mask is None else f"&0x{self.mask:X}"
        return f"((w>>{self.shr}){m})<<{self.shl}@0x{self.key[0]:08X}+0x{self.key[1]:X}"


class Site:
    def __init__(self, img, off):
        self.img, self.off = img, off
        self.slot_va = None       # where the destination word was read FROM
        self.dest = None          # the destination address the loader writes to
        self.reader = None        # the jal target that performs the read
        self.desc = None          # (lba, nbytes) as recovered
        self.form = None          # 'struct' | 'reg' | 'table'
        self.file = None          # the disc file the descriptor names
        self.note = ""
        self.table = None         # (word_va, lba_field, size_field) for the indexed form
        self.opener = None        # the jal target the descriptor was passed to
        self.npaths = 0           # straight-line paths through the block that reach this site

    def cite(self):
        a = self.img.va(self.off)
        w = self.img.w[self.off // 4]
        loc = f"{self.img.stem}+0x{self.off:X}" if a is None else f"0x{a:08X}"
        return f"{loc}  {w:08X}  {re_crt0.disasm1(w, a or self.off)}"


def const_block(w, start, end):
    """Concretely interpret [start,end] linearly, tracking register values and sp-relative stores.

    Deliberately NOT a full CPU: it resolves exactly the idioms a loader call site uses to build its
    arguments — lui/ori/addiu/andi, addu with $zero, sll/srl, `sw` to sp+K, and `lw` from a constant
    table at base+(index<<2). A value it cannot follow becomes UNKNOWN and the site is then reported
    UNRESOLVED; the one thing it must never do is invent a value. Branches are NOT followed: the
    descriptor of every loader site in this image is built in the entry block, and a site whose
    arguments come from elsewhere shows up as UNRESOLVED rather than as a wrong answer.

    A register holds one of: an int, ("sp", K) for a stack address, ("idx", tableBaseVA) for a
    computed table element address, or a Fld (a field of a word loaded from a constant table).
    """
    reg = {0: 0}
    stk = {}

    def put(r, v):
        if r == 0:
            return
        if v is None:
            reg.pop(r, None)
        else:
            reg[r] = v

    for k in range(start, end + 1):
        y = w[k]
        op = y >> 26
        rs, rt, imm = (y >> 21) & 31, (y >> 16) & 31, y & 0xFFFF
        simm = imm - 0x10000 if imm & 0x8000 else imm
        a = reg.get(rs)
        if op == 0x0F:                                       # lui
            put(rt, (imm << 16) & 0xFFFFFFFF)
        elif op == 0x09:                                     # addiu
            put(rt, ("sp", imm) if rs == 29 else
                    ((a + simm) & 0xFFFFFFFF if isinstance(a, int) else None))
        elif op == 0x0D:                                     # ori
            put(rt, (a | imm) if isinstance(a, int) else None)
        elif op == 0x0C:                                     # andi
            if isinstance(a, int):
                put(rt, a & imm)
            elif isinstance(a, Fld) and a.mask is None and a.shl == 0:
                put(rt, a.with_(mask=imm))
            else:
                put(rt, None)
        elif op == 0x23:                                     # lw rt, imm(rs)
            if rs == 29:
                put(rt, stk.get(imm))
            elif isinstance(a, tuple) and a[0] == "idx":
                put(rt, Fld((a[1], imm)))
            else:
                put(rt, None)
        elif op == 0x2B:                                     # sw rt, imm(rs)
            if rs == 29:
                stk[imm] = reg.get(rt)
        elif op == 0:
            f = y & 0x3F
            rd, sa = (y >> 11) & 31, (y >> 6) & 31
            b = reg.get(rt)
            if f in (0x20, 0x21):                            # add / addu
                if rt == 0:
                    put(rd, a)
                elif rs == 0:
                    put(rd, b)
                elif isinstance(a, tuple) and a[0] == "sh2" and isinstance(b, int):
                    put(rd, ("idx", b))
                elif isinstance(b, tuple) and b[0] == "sh2" and isinstance(a, int):
                    put(rd, ("idx", a))
                else:
                    put(rd, None)
            elif f == 0x00:                                  # sll rd, rt, sa
                if sa == 2 and not isinstance(b, (int, Fld)):
                    put(rd, ("sh2", rt))                     # an index scaled to a word
                elif isinstance(b, int):
                    put(rd, (b << sa) & 0xFFFFFFFF)
                elif isinstance(b, Fld) and b.shl == 0:
                    put(rd, b.with_(shl=sa))
                elif sa == 2:
                    put(rd, ("sh2", rt))
                else:
                    put(rd, None)
            elif f == 0x02:                                  # srl rd, rt, sa
                if isinstance(b, int):
                    put(rd, b >> sa)
                elif isinstance(b, Fld) and b.shr == 0 and b.mask is None and b.shl == 0:
                    put(rd, b.with_(shr=sa))
                else:
                    put(rd, None)
            else:
                put(rd, None)
        elif op in (0x20, 0x21, 0x24, 0x25, 0x28, 0x29, 0x0A, 0x0B, 0x0E, 0x18, 0x19):
            put(rt, None)                                    # lb/lh/lbu/lhu/slti/xori/... unfollowed
    return reg, stk


def slot_reads(img, exe, hdr):
    """Every `lui rX,hi / lw rD,K(rX)` into an ARGUMENT register whose effective address lands in the
    RESIDENT image AND whose word (read out of the executable's own bytes) is a KSEG0 RAM address.

    Nothing here assumes where the destination table is: the sites define it, and the report prints
    the addresses they turned out to name. The KSEG0 filter is what separates a destination-pointer
    load from the thousands of ordinary global loads in these 21 images — a global holding a value
    that is a valid 2 MB RAM address AND is passed straight to a call that also carries a
    disc-validated (lba, size) descriptor is a loader site; the disc referee decides the rest.
    """
    lo, hi = hdr["t_addr"], hdr["t_addr"] + hdr["t_size"]
    out = []
    w = img.w
    for i in range(1, len(w)):
        x, p = w[i], w[i - 1]
        if (x >> 26) != 0x23 or (p >> 26) != 0x0F:
            continue
        rs, rd, imm = (x >> 21) & 31, (x >> 16) & 31, x & 0xFFFF
        if ((p >> 16) & 31) != rs or rd not in ARG_REGS:
            continue
        simm = imm - 0x10000 if imm & 0x8000 else imm
        va = (((p & 0xFFFF) << 16) + simm) & 0xFFFFFFFF
        if not (lo <= va < hi):
            continue
        word = struct.unpack_from("<I", exe.data, va - lo + EXE_HEADER)[0]
        if not (0x80000000 <= word < 0x80200000) or word % 4:
            continue
        s = Site(img, i * 4)
        s.slot_va, s.dest, s.destreg = va, word, rd
        out.append(s)
    return out


JAL_WINDOW = 12     # instructions after the slot read in which the consuming call must appear


def resolve_site(site, bylba, tables):
    """Recover the site's (lba, nbytes) and match it against the disc. Sets .desc/.file/.form."""
    w = site.img.w
    i = site.off // 4
    ent = [e // 4 for e in entry_offsets(w) if e // 4 <= i]
    start = ent[-1] if ent else max(0, i - 64)
    jal = None
    for k in range(i, min(i + JAL_WINDOW, len(w))):
        if (w[k] >> 26) == 3:
            jal = k
            break
    if jal is None:
        site.note = (f"no `jal` within {JAL_WINDOW} instructions of the pointer load — "
                     "not a loader call site")
        return
    site.reader = 0x80000000 | ((w[jal] & 0x03FFFFFF) << 2)
    reg, stk = const_block(w, start, jal + 1)     # +1: the delay slot sets an argument

    vals = []                                     # every candidate argument value, int or Fld
    for r in ARG_REGS:
        v = reg.get(r)
        if isinstance(v, (int, Fld)):
            vals.append(v)
        elif isinstance(v, tuple) and v[0] == "sp":
            for d in (0, 4):
                x = stk.get(v[1] + d)
                if isinstance(x, (int, Fld)):
                    vals.append(x)
    flds = [v for v in vals if isinstance(v, Fld)]
    nums = [v for v in vals if isinstance(v, int)]

    if len(flds) >= 2:
        resolve_table(site, flds, tables)
        return
    for n, a in enumerate(nums):
        for m, b in enumerate(nums):
            if n == m:
                continue
            if match_disc(site, a, b, bylba):
                site.form = "reg/stack"
                return
    site.note = ("candidate arguments " + repr(sorted(set(nums))) +
                 " — no ordered pair among them is (lba, byteCount) for a real file on this disc"
                 if nums else
                 "the call's arguments do not resolve to constants in the entry block "
                 f"({[repr(v) for v in vals]})")


def match_disc(site, lba, nbytes, bylba):
    """The DISC is the referee: lba must start a real file and nbytes must cover it, whole sectors."""
    if lba not in bylba or nbytes == 0 or nbytes % SECTOR or nbytes > 0x200000:
        return False
    path, size = bylba[lba]
    if nbytes < pad2k(size):
        return False
    site.desc, site.file = (lba, nbytes), path
    if nbytes > pad2k(size):
        site.note = (f"OVER-READ: the loader reads 0x{nbytes:X} bytes for a {size}-byte file "
                     f"(0x{pad2k(size):X} padded) — it reads on through the sectors that follow")
    return True


def resolve_table(site, flds, tables):
    """The indexed form: the arguments are FIELDS of one packed word from a constant table.

    The field decode (`srl n` / `andi m` / `sll s`) is read off the instructions, never assumed, and
    the table's address comes from the lui/addiu pair in the same block. Enumerating it needs the
    CONTAINING module's base, which M2 supplies independently — and the table landing inside that
    module's own data is itself a check on that base.
    """
    keys = {f.key for f in flds}
    if len(keys) != 1:
        site.note = ("the arguments are fields of DIFFERENT table entries " +
                     repr(sorted(keys)) + " — not one packed descriptor word")
        return
    site.form = "table"
    tva, off = keys.pop()
    site.table = (tva + off, tuple(sorted((f.shr, f.mask if f.mask is not None else 0xFFFFFFFF,
                                           f.shl) for f in flds)))
    tables.setdefault(site.table, []).append(site)


def enumerate_table(table, imgs, bylba):
    """Walk a packed (lba<<shr | sectors) table out of whichever module contains it. Stops at the
    first entry that does not name a real file — the table's LENGTH is measured, not declared."""
    tva, shr, shl = table
    host = None
    for im in imgs.values():
        if im.base is not None and im.off_of(tva) is not None:
            host = im
            break
    if host is None:
        return None, [], "no measured module contains that table address"
    off = host.off_of(tva)
    mask = (1 << shr) - 1
    ents, i = [], 0
    while off + 4 * i + 4 <= len(host.data):
        word = struct.unpack_from("<I", host.data, off + 4 * i)[0]
        lba, nbytes = word >> shr, (word & mask) << shl
        if lba not in bylba:
            break
        path, size = bylba[lba]
        if nbytes < pad2k(size):
            break
        ents.append((i, word, lba, nbytes, path, size))
        i += 1
    return host, ents, ""


# ------------------------------------------------------------------------------ the measurement --

class Result:
    def __init__(self):
        self.slots = []          # ordered distinct destination addresses, with the VAs they came from
        self.slot_of = {}        # dest -> index
        self.sites = []
        self.tables = {}
        self.table_ents = {}
        self.bases = {}          # stem -> (base, how)
        self.disagree = []       # M1 file-specific destination vs M2
        self.ref_checks = []     # (path, sha1, m2 base, reference base)
        self.ref_missing = []
        self.ref_sha_mismatch = []
        self.ref_disagree = []
        self.ref_extra = []
        self.thin = []
        self.undecided = []
        self.empty = []
        self.unresolved = []
        self.n_disc_code = 0
        self.hdr = None


def measure(disc):
    files, images = code_images(disc)
    imgs, failed, empty = extract_all(disc, images)
    if failed:
        raise Refuse("could not extract " + ", ".join(failed) + " — measured NOTHING for them")
    exe = imgs.get(EXE_ON_DISC)
    if exe is None:
        raise Refuse(f"{EXE_ON_DISC} was not extracted — nothing to measure")
    bylba = {}
    for p, l, s in files:
        bylba.setdefault(l, (p, s))

    r = Result()
    r.n_disc_code = len(images)
    r.empty = empty
    r.hdr = psexe(exe.data)

    # --- M2 first: every module's base from its own bytes, independent of any loader -------------
    for name, im in sorted(imgs.items()):
        best, hits, second, ne, nt = sweep(im)
        im.m2 = (best, hits, second, ne, nt)
        ratio = hits / max(second, 1)
        if best is None or hits < M2_MIN_HITS or ratio < M2_MIN_RATIO:
            r.undecided.append((im.stem, best, hits, second, ne, nt))
            continue
        im.base = best
        if ratio < M2_THIN_RATIO:
            r.thin.append((im.stem, best, hits, second, ratio))

    # --- M1: the loader sites, refereed by the disc ----------------------------------------------
    for name, im in sorted(imgs.items()):
        for s in slot_reads(im, exe, r.hdr):
            resolve_site(s, bylba, r.tables)
            r.sites.append(s)
    for t, sites in sorted(r.tables.items()):
        host, ents, why = enumerate_table(t, imgs, bylba)
        r.table_ents[t] = (host, ents, why)

    # --- M1 vs M2 per module (only a disc-resolved PRG descriptor can name a module) --------------
    m1 = {}          # stem -> set of destinations M1 says it is loaded to
    for s in r.sites:
        if s.file and s.file.upper().endswith(".PRG"):
            m1.setdefault(os.path.splitext(os.path.basename(s.file))[0], set()).add(s.dest)
    for t, (host, ents, _why) in r.table_ents.items():
        dests = {s.dest for s in r.tables[t]}
        for _i, _w, _l, _b, path, _sz in ents:
            if path.upper().endswith(".PRG"):
                m1.setdefault(os.path.splitext(os.path.basename(path))[0], set()).update(dests)

    # --- M3: bind every reference vram to OUR bytes by SHA-1, then compare it with M2 -------------
    refs = reference_records()
    owned_prgs = {im.name.upper() for im in imgs.values() if im.name.upper().endswith(".PRG")}
    r.ref_extra = sorted(set(refs) - owned_prgs)
    for name, im in sorted(imgs.items()):
        if name == EXE_ON_DISC:
            continue
        key = im.name.upper()
        rec = refs.get(key)
        if rec is None:
            r.ref_missing.append(im.name)
            continue
        verdict, digest = reference_verdict(im, rec)
        if verdict == "sha":
            r.ref_sha_mismatch.append((im.name, digest, rec["sha1"]))
            continue
        if verdict == "no-m2":
            continue
        r.ref_checks.append((im.name, digest, im.base, rec["base"]))
        if verdict == "base":
            r.ref_disagree.append((im.name, im.base, rec["base"]))
            continue
        cand = m1.get(im.stem)
        if cand is not None and im.base not in cand:
            r.disagree.append((im.stem, im.base, sorted(cand)))
            continue
        how = "M2+M3" + ("+M1" if cand is not None else "")
        r.bases[im.stem] = (im.base, how)

    # The loader/base slots are the distinct bases shared by verified modules. M1 independently
    # exposes resident words containing all three values, even though it cannot recover file names
    # for those call paths; cite those read locations without pretending the other candidates are
    # loader slots.
    for dest in sorted({base for base, _how in r.bases.values()}):
        vas = sorted({s.slot_va for s in r.sites if s.dest == dest})
        r.slot_of[dest] = len(r.slots)
        r.slots.append((dest, vas))
    for s in r.sites:
        if not (s.file or s.table):
            r.unresolved.append(s)
    return r, imgs, exe


# ----------------------------------------------------------------------------------- reporting --

def report(r, imgs, out=print):
    h = r.hdr
    out("== denominators " + "=" * 62)
    out(f"  code images on the disc (boot exe + *.PRG) : {r.n_disc_code}")
    out(f"  images extracted and measured              : {len([i for i in imgs])}")
    out(f"  images with NO code (0 bytes on the disc)  : {len(r.empty)} {r.empty}")
    out(f"  slot-read sites scanned                    : {len(r.sites)}")
    out(f"  ... resolved to a disc file directly       : {len([s for s in r.sites if s.file])}")
    out(f"  ... resolved to an indexed LBA table       : {len([s for s in r.sites if s.table])}")
    out(f"  ... UNRESOLVED                             : {len(r.unresolved)}")
    out(f"  boot exe PS-EXE t_addr=0x{h['t_addr']:08X} t_size=0x{h['t_size']:X} "
        f"(file offset 0 therefore loads at 0x{h['t_addr'] - EXE_HEADER:08X})")

    out("")
    out("== verified overlay slots (distinct M2+M3 module bases) " + "=" * 22)
    for i, (dest, vas) in enumerate(r.slots):
        reads = ", ".join(f"0x{v:08X}" for v in vas) if vas else "NO resident candidate read"
        out(f"  slot {i}: 0x{dest:08X}   resident candidate read(s): {reads}")
    if r.slots:
        vas = sorted({v for _d, vs in r.slots for v in vs})
        if vas:
            out(f"  the sites read {len(vas)} distinct words spanning 0x{vas[0]:08X}..0x{vas[-1]:08X} "
                f"— contiguous: {vas == list(range(vas[0], vas[-1] + 1, 4))}")

    out("")
    out("== M1: each loader site, with the disc as referee " + "=" * 29)
    for s in sorted(r.sites, key=lambda s: (s.img.stem, s.off)):
        tag = s.file or ("indexed table @0x%08X" % s.table[0] if s.table else "UNRESOLVED")
        out(f"  {s.cite()}")
        out(f"      dest 0x{s.dest:08X} (slot {r.slot_of.get(s.dest, '?')}) via reader "
            f"0x{s.reader:08X}" if s.reader else "      no reader")
        if s.desc:
            out(f"      descriptor form={s.form} lba={s.desc[0]} bytes=0x{s.desc[1]:X} -> {tag}")
        elif s.table:
            out(f"      descriptor form=table lba=word>>{s.table[1]} "
                f"bytes=(word&0x{(1 << s.table[1]) - 1:X})<<{s.table[2]} from 0x{s.table[0]:08X}")
        if s.note:
            out(f"      NOTE {s.note}")

    for t, (host, ents, why) in sorted(r.table_ents.items()):
        out("")
        out(f"== the indexed LBA table at 0x{t[0]:08X} " + "=" * 34)
        if host is None:
            out(f"  CANNOT ENUMERATE: {why}")
            continue
        out(f"  it lies in {host.stem} at +0x{host.off_of(t[0]):X} (that module's measured base "
            f"0x{host.base:08X} is what places it there — an independent check on the base)")
        out(f"  {len(ents)} entries resolve to a real disc file; entry {len(ents)} does not, "
            "which is where the table ends")
        for i, word, lba, nbytes, path, size in ents:
            note = "" if nbytes == pad2k(size) else f"  OVER-READ (file {size} B, padded 0x{pad2k(size):X})"
            out(f"    [{i:2}] 0x{word:08X} lba={lba:6} bytes=0x{nbytes:<6X} -> {path}{note}")

    out("")
    out("== M2: base from each module's OWN bytes (jal targets x function entries) " + "=" * 6)
    for name, im in sorted(imgs.items()):
        best, hits, second, ne, nt = im.m2
        ratio = hits / max(second, 1)
        mark = "OK  "
        if im.base is None:
            mark = "NONE"
        elif ratio < M2_THIN_RATIO:
            mark = "THIN"
        b = "        --" if best is None else f"0x{best:08X}"
        out(f"  {mark} {im.stem:10} {b}  hits={hits:4} runner-up={second:3} margin={ratio:5.2f}x  "
            f"(entries={ne} jal-targets={nt})")

    out("")
    out("== M3: rood-reverse identity + link-address corroboration " + "=" * 17)
    for path, digest, m2, ref in sorted(r.ref_checks):
        out(f"  {'OK' if m2 == ref else 'DISAGREE':8} {path:24} sha1={digest[:12]}…  "
            f"M2=0x{m2:08X} rood-vram=0x{ref:08X}")
    out(f"  checked {len(r.ref_checks)} owned non-empty .PRG images; "
        f"missing-config={len(r.ref_missing)} sha-mismatch={len(r.ref_sha_mismatch)} "
        f"address-disagreement={len(r.ref_disagree)} extra-config={len(r.ref_extra)}")

    out("")
    out("== MEASURED load base per module " + "=" * 46)
    for stem, (base, how) in sorted(r.bases.items()):
        out(f"  {stem:10} 0x{base:08X}  slot {r.slot_of.get(base, '?')}  [{how}]")
    out(f"  measured: {len(r.bases)} modules")

    out("")
    out("== what this run could NOT see " + "=" * 48)
    if r.empty:
        out(f"  {r.empty}: 0 bytes on this disc. No code, so no base exists to measure. NOT a gap.")
    for s in r.unresolved:
        out(f"  UNRESOLVED site {s.cite().strip()} -> dest 0x{s.dest:08X}: {s.note}")
    for stem, best, hits, second, ne, nt in r.undecided:
        b = "none" if best is None else f"0x{best:08X}"
        out(f"  M2 UNDECIDED for {stem}: best={b} hits={hits} runner-up={second} "
            f"(entries={ne} jal-targets={nt}) — below the {M2_MIN_HITS}-hit / {M2_MIN_RATIO}x bar")
    for stem, base, cand in r.disagree:
        out(f"  DISAGREEMENT {stem}: M2 says 0x{base:08X}, M1 says " +
            ", ".join(f"0x{c:08X}" for c in cand))
    for path in r.ref_missing:
        out(f"  M3 MISSING CONFIG for owned image {path}")
    for path, got, want in r.ref_sha_mismatch:
        out(f"  M3 IDENTITY FAILURE {path}: owned sha1={got}, rood config sha1={want}")
    for path, m2, ref in r.ref_disagree:
        out(f"  M3 ADDRESS DISAGREEMENT {path}: M2=0x{m2:08X}, rood-vram=0x{ref:08X}")
    for path in r.ref_extra:
        out(f"  M3 EXTRA CONFIG {path}: no owned non-empty .PRG image was extracted for it")
    out("  Method blind spots, stated rather than implied:")
    out("   - M1 reads the loader's STATIC descriptors. A module loaded only through a code path this")
    out("     scanner's idiom does not cover would be absent, not wrong; the site count above is the")
    out("     denominator for that.")
    out("   - M2 assumes non-leaf functions open with `addiu $sp,$sp,-N`. It cannot decide a module")
    out("     with too few such entries (printed UNDECIDED), and its margin is printed for every one.")
    out("   - None of the methods observes a RUNNING loader. M2 reads owned bytes; M3 reads the")
    out("     vendored config only after binding it to those bytes by SHA-1; M1 statically reads the")
    out("     resident executable. Runtime rewriting remains outside this instrument's reach.")
    failures = (r.disagree or r.undecided or r.ref_missing or r.ref_sha_mismatch or
                r.ref_disagree or r.ref_extra)
    if not failures and r.bases:
        out("")
        out(f"RESULT: {len(r.bases)} non-empty modules VERIFIED at {len(r.slots)} distinct slots; "
            f"M2 and SHA-bound M3 agree for all {len(r.ref_checks)}. M1 found candidate resident "
            f"reads for {len([v for _d, v in r.slots if v])}/{len(r.slots)} slots but left "
            f"{len(r.unresolved)} candidate sites unresolved; that is a stated M1 coverage limit, "
            "not a missing module mapping.")
    return 1 if failures else 0


# --------------------------------------------------------------------- the shipping-config gates --

def parse_config(text):
    """The 3 `.overlaySlots` bases out of the SHIPPING game_config.cpp, by text."""
    lines = [line for line in text.splitlines() if ".overlaySlots" in line]
    if not lines:
        raise Refuse(f"{CONFIG_SRC} has no .overlaySlots initialiser — nothing to check")
    if len(lines) != 1:
        raise Refuse(f"{CONFIG_SRC} has {len(lines)} lines containing .overlaySlots; expected one")
    toks = re.findall(r"\{\s*(0[xX][0-9a-fA-F]+|[0-9]+)\s*,\s*nullptr\s*\}", lines[0])
    if len(toks) != 3:
        raise Refuse(f".overlaySlots must contain exactly 3 literal-base/null-callback entries on "
                     f"one line; parsed {len(toks)} from {lines[0]!r}")
    return [int(tok, 0) for tok in toks]


def parse_seeds(text):
    """overlay_bases out of recomp_seeds.json. Its `//` comments are stripped the way emit.py does."""
    lines = [ln for ln in text.splitlines() if not ln.lstrip().startswith("//")]
    import json
    data = json.loads("\n".join(lines))
    return {k: int(v, 0) if isinstance(v, str) else v
            for k, v in data.get("overlay_bases", {}).items()}


def check_config(r, out=print, config_text=None, seeds_text=None):
    if config_text is None:
        config_text = open(CONFIG_SRC, encoding="utf-8").read()
    if seeds_text is None:
        seeds_text = open(SEEDS_SRC, encoding="utf-8").read()
    cfg = parse_config(config_text)
    seeds = parse_seeds(seeds_text)
    want_slots = [d for d, _v in r.slots]
    fails = 0
    checks = 0

    out("== --check-config: the SHIPPING files vs these bytes " + "=" * 26)
    out(f"  game_config.cpp .overlaySlots      : {len(cfg)} entries")
    out(f"  recomp_seeds.json overlay_bases    : {len(seeds)} entries")
    out(f"  measured slots {len(want_slots)} · measured modules {len(r.bases)}")
    if len(cfg) != len(want_slots):
        out(f"  FAILED slot count: config has {len(cfg)}, measurement found {len(want_slots)}")
        fails += 1
    checks += 1
    for i, (dest, _vas) in enumerate(r.slots):
        checks += 1
        got = cfg[i] if i < len(cfg) else None
        ok = got == dest
        fails += 0 if ok else 1
        out(f"  {'ok    ' if ok else 'FAILED'} overlaySlots[{i}].base "
            f"config={('0x%08X' % got) if got is not None else 'MISSING':>10} "
            f"measured=0x{dest:08X}")
    for stem, (base, how) in sorted(r.bases.items()):
        checks += 1
        got = seeds.get(stem)
        ok = got == base
        fails += 0 if ok else 1
        out(f"  {'ok    ' if ok else 'FAILED'} overlay_bases[{stem}] "
            f"seeds={('0x%08X' % got) if got is not None else 'MISSING':>10} "
            f"measured=0x{base:08X} [{how}]")
    extra = sorted(set(seeds) - set(r.bases))
    for stem in extra:
        checks += 1
        fails += 1
        out(f"  FAILED overlay_bases[{stem}] is declared in the seeds but NOTHING was measured for "
            "it — a base with no measurement behind it is exactly what this gate exists to stop")
    out(f"  {checks} checks, {fails} FAILED")
    return 1 if fails else 0


# ---------------------------------------------------------------------------------- the selftest --

def selftest(disc, out=print):
    """Every claim this tool makes, fed a case that MUST come out the OTHER way."""
    out("== selftest plan: 7 checks, each one a case whose answer is known WITHOUT this tool " + "=" * 1)
    for i, t in enumerate([
        "M2 recovers the boot exe's OWN load address, known independently from its PS-EXE header",
        "M2 on a module shifted by one word must NOT still answer the unshifted base",
        "M2 refuses (UNDECIDED) a module whose function entries have been destroyed",
        "M3 rejects an owned image changed by one byte BEFORE comparing its address",
        "M3 rejects a reference vram changed by one word after identity passes",
        "M1's disc referee REJECTS a descriptor whose LBA is not a file start",
        "--check-config names BOTH a changed shipping slot and a changed module seed",
    ], 1):
        out(f"   [{i}] {t}")
    out("")
    fails = []

    files, images = code_images(disc)
    imgs, failed, _empty = extract_all(disc, images)
    if failed:
        raise Refuse("selftest could not extract " + ", ".join(failed))
    exe = imgs[EXE_ON_DISC]
    hdr = psexe(exe.data)
    refs = reference_records()
    bylba = {}
    for p, l, s in files:
        bylba.setdefault(l, (p, s))

    # [1] ground truth: the exe's own header says where file offset 0 lands.
    truth = hdr["t_addr"] - EXE_HEADER
    best, hits, second, _ne, _nt = sweep(exe)
    ok = best == truth
    out(f"  [1] {'PASS' if ok else 'FAIL'} M2(SLUS_010.40) = 0x{best:08X}, PS-EXE header says "
        f"0x{truth:08X} (t_addr 0x{hdr['t_addr']:08X} - 0x{EXE_HEADER:X} header) "
        f"hits={hits} runner-up={second}")
    if not ok:
        fails.append(1)

    # [2] shift the whole image by one word: the true base must move with it.
    bat = imgs["BATTLE.PRG"]
    shifted = Img("shift", b"\x00\x00\x00\x00" + bat.data)
    b2, h2, s2, _a, _b = sweep(shifted)
    real, hr, _sr, _c, _d = sweep(bat)
    ok = b2 == (real - 4) & 0xFFFFFFFF and b2 != real
    out(f"  [2] {'PASS' if ok else 'FAIL'} BATTLE base 0x{real:08X} (hits {hr}); with one word "
        f"prepended M2 answers 0x{b2:08X} (hits {h2}, runner-up {s2}) — it tracks the shift, so it "
        "is reading placement and not printing a constant")
    if not ok:
        fails.append(2)

    # [3] destroy every function entry: there must be NO answer, not a confident wrong one.
    w = list(bat.w)
    for i, x in enumerate(w):
        if (x >> 16) == 0x27BD and (x & 0x8000):
            w[i] = 0x00000000
    wrecked = Img("wrecked", struct.pack("<%dI" % len(w), *w))
    b3, h3, s3, ne3, _nt3 = sweep(wrecked)
    ok = ne3 == 0 and (b3 is None or h3 < M2_MIN_HITS)
    out(f"  [3] {'PASS' if ok else 'FAIL'} with all {len(entry_offsets(bat.w))} `addiu $sp,-N` "
        f"entries zeroed: entries={ne3} best={b3} hits={h3} runner-up={s3} — "
        "no entries means no answer")
    if not ok:
        fails.append(3)

    # [4] M3 must bind the reference to the owned bytes before it trusts the address.
    bat.base = real
    rec = refs[bat.name.upper()]
    changed = bytearray(bat.data)
    changed[-1] ^= 1
    changed_img = Img(bat.name, bytes(changed))
    changed_img.base = real
    verdict4, digest4 = reference_verdict(changed_img, rec)
    ok = verdict4 == "sha"
    out(f"  [4] {'PASS' if ok else 'FAIL'} one owned byte changed: verdict={verdict4}, "
        f"sha1={digest4[:12]}… expected={rec['sha1'][:12]}… — address was not accepted")
    if not ok:
        fails.append(4)

    # [5] M3 must independently reject a wrong reference address after SHA identity succeeds.
    wrong_rec = dict(rec)
    wrong_rec["base"] += 4
    verdict5, _digest5 = reference_verdict(bat, wrong_rec)
    ok = verdict5 == "base"
    out(f"  [5] {'PASS' if ok else 'FAIL'} owned SHA-1 matches but rood-vram moved +4: "
        f"verdict={verdict5}, M2=0x{real:08X}, changed-vram=0x{wrong_rec['base']:08X}")
    if not ok:
        fails.append(5)

    # [6] the referee must say NO to a bad LBA. Pick an LBA no file starts at.
    bad = next(l for l in range(1, 100000) if l not in bylba)
    probe = Site(exe, 0)
    rejected = not match_disc(probe, bad, 0x800, bylba)
    good = next((l, pad2k(s)) for l, (p, s) in sorted(bylba.items()) if s and p.endswith(".PRG"))
    probe2 = Site(exe, 0)
    accepted = match_disc(probe2, good[0], good[1], bylba)
    ok = rejected and accepted
    out(f"  [6] {'PASS' if ok else 'FAIL'} referee rejects lba={bad} (no file starts there): "
        f"{rejected}; accepts lba={good[0]} bytes=0x{good[1]:X} -> {probe2.file}: {accepted}")
    if not ok:
        fails.append(6)

    # [7] the config gate must go RED on a one-word change to a SHIPPING value.
    r, _i2, _e2 = measure(disc)
    text = open(CONFIG_SRC, encoding="utf-8").read()
    cfg = parse_config(text)
    old = f"{{0x{cfg[0]:08X}, nullptr}}"
    new = f"{{0x{cfg[0] + 4:08X}, nullptr}}"
    if text.count(old) != 1:
        raise Refuse(f"selftest could not uniquely locate shipping slot text {old!r}")
    bad_text = text.replace(old, new)
    seeds_text = open(SEEDS_SRC, encoding="utf-8").read()
    seed_old = f'"BATTLE": "0x{r.bases["BATTLE"][0]:08X}"'
    seed_new = f'"BATTLE": "0x{r.bases["BATTLE"][0] + 4:08X}"'
    if seeds_text.count(seed_old) != 1:
        raise Refuse(f"selftest could not uniquely locate shipping seed text {seed_old!r}")
    bad_seeds = seeds_text.replace(seed_old, seed_new)
    sink = []
    rc = check_config(r, out=sink.append, config_text=bad_text, seeds_text=bad_seeds)
    slot_line = next((ln.strip() for ln in sink if "FAILED overlaySlots[0]" in ln), "MISSING")
    seed_line = next((ln.strip() for ln in sink if "FAILED overlay_bases[BATTLE]" in ln), "MISSING")
    ok = rc == 1 and slot_line != "MISSING" and seed_line != "MISSING"
    out(f"  [7] {'PASS' if ok else 'FAIL'} with SHIPPING slot 0 and BATTLE seed moved +4, "
        f"the gate returns {rc} and prints BOTH: {slot_line}; {seed_line}")
    if not ok:
        fails.append(7)

    out("")
    passed = 7 - len(fails)
    out(f"selftest: 7 checks, {passed} PASS, 0 SKIP, {len(fails)} FAIL "
        f"{fails if fails else ''}")
    out("  Not covered by this selftest, stated explicitly: nothing here observes a RUNNING loader, "
        "so a base that is correct statically but rewritten at run time would pass every check "
        "above. The resident substrate stops at BIOS A0:0x2F before the loader (RE-04).")
    return 1 if fails else 0


def main(argv):
    ap = argparse.ArgumentParser(add_help=True, description=__doc__.splitlines()[0])
    ap.add_argument("disc", nargs="?")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--check-config", action="store_true")
    a = ap.parse_args(argv)
    try:
        disc = resolve(a.disc, verbose=not (a.selftest or a.check_config))
        if a.selftest:
            return selftest(disc)
        r, imgs, _exe = measure(disc)
        if a.check_config:
            return check_config(r)
        return report(r, imgs)
    except Refuse as e:
        print(f"[re_overlay] REFUSING: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
