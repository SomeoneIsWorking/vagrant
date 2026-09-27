#!/usr/bin/env python3
"""Census Vagrant Story's guest projection publication and its horizontal-bound consumers.

WHAT THIS TOOL ANSWERS, PRECISELY. It answers two questions about the vendored CC0
`external/rood-reverse` DECOMPILATION:

  1. Which decompiled sites WRITE, and which READ, the specific named words that hold a horizontal
     extent or a projection parameter for this title?
  2. Do the guest addresses this repository SHIPS name the same things the decompilation's own
     per-module symbol map (`config/*/symbol_addrs.txt`) names at those addresses?

WHAT IT DOES NOT ANSWER, AND SAYS SO ON EVERY RUN. It does not answer "does the guest cull
horizontally". A decompilation is a partial RECONSTRUCTION: most of BATTLE.PRG's text segment is
not decompiled in this vendored tree, so a zero here means "no decompiled site names this word",
never "the guest has no such consumer". The text-segment coverage is measured and reported, so a
reader can see how much of the module the answer is drawn from.

WHY IT EXISTS. `docs/project-state.md` records S010 (true widescreen) as `missing`, and
`docs/battle-rendering.md` records the projection boundary from a byte measurement. This tool is
the part of that claim which a decompilation can falsify: it turns "the projection is published at
one place" and "nothing decompiled consumes the horizontal extent as a bound" into statements with
a file/line citation and a denominator, and it gates every shipped address against the
decompilation's module map so a guessed address cannot enter the tree quietly.

NO DISK REQUIRED. The decompilation is vendored source, so this instrument runs with no game image.
That is exactly why its output is worded as a reconstruction reading and never as a measurement of
the compiled game.
"""

import os
import re
import sys

from re_crt0 import Refuse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DECOMP = os.path.join(ROOT, "external", "rood-reverse")
DECOMP_SRC = os.path.join(DECOMP, "src")
MODULE_MAPS = (
    os.path.join(DECOMP, "config", "SLUS_010.40", "symbol_addrs.txt"),
    os.path.join(DECOMP, "config", "BATTLE", "BATTLE.PRG", "symbol_addrs.txt"),
    os.path.join(DECOMP, "config", "ENDING", "ENDING.PRG", "symbol_addrs.txt"),
    os.path.join(DECOMP, "config", "MENU", "MAINMENU.PRG", "symbol_addrs.txt"),
)
FACTS_HEADERS = (
    os.path.join(ROOT, "game", "render", "battle_projection_facts.h"),
    os.path.join(ROOT, "game", "render", "title_splash_facts.h"),
)

SOURCE_SUFFIXES = (".c", ".h", ".s")

# The words a horizontal extent or a projection parameter can live in, with the decompilation's own
# name for each. `D_8005DFD4/6/8/A` are four adjacent shorts the publication function writes as a
# rectangle: x, y, w, h in that order. They are watched separately because the census has to be able
# to say WHICH of the four is read, not merely that "the rect" is read.
WATCHED_WORDS = (
    "D_8005DFD4",
    "D_8005DFD6",
    "D_8005DFD8",
    "D_8005DFDA",
    "vs_main_projectionDistance",
    "vs_main_nearClip",
    "vs_scratch.camera.farClip",
    "SetGeomOffset",
    "SetGeomScreen",
    "SetDefDrawEnv",
    "SetDefDispEnv",
    "NormalClip",
)

# The module each watched word is documented to live in, and the module-map file that must name it.
# An empty module means "any module" and the census only records where it was actually found.
WORD_HOME = {
    "D_8005DFD4": "SLUS_010.40",
    "D_8005DFD6": "SLUS_010.40",
    "D_8005DFD8": "SLUS_010.40",
    "D_8005DFDA": "SLUS_010.40",
    "vs_main_projectionDistance": "SLUS_010.40",
    "vs_main_nearClip": "SLUS_010.40",
    "SetGeomOffset": "SLUS_010.40",
    "SetGeomScreen": "SLUS_010.40",
    "SetDefDrawEnv": "SLUS_010.40",
    "SetDefDispEnv": "SLUS_010.40",
    "vs_scratch.camera.farClip": "BATTLE.PRG",
    "NormalClip": "SLUS_010.40",
}

# Every address the title ships, as a name the decompilation's module map also uses. The census
# diffs the SHIPPING value against the module map, so a constant that no module names at all is a
# finding rather than a fact. This is the "the shipped value must be compared to the measured one, by
# code" rule applied to a reconstruction: the module map is an independent statement of what lives
# at an address, produced by a different toolchain from the byte measurement in tools/re_frame.py.
SHIPPED_ADDRESSES = {
    "kSetDefDrawEnv": 0x8002B374,
    "kSetDefDispEnv": 0x8002B434,
    "kSetGeomOffset": 0x80041540,
    "kSetGeomScreen": 0x80041534,
    "kDrawSync": 0x80028650,
    "kDrawOTag": 0x80028C44,
    "kPutDrawEnv": 0x80028CB4,
    "kPutDispEnv": 0x80028E80,
    "kBattleViewportPublication": 0x800760CC,
    "kBattleFieldPresenter": 0x8007629C,
    "kBattleProjectionDistanceSetter": 0x8007CCF0,
    "kBattleNearClipSetter": 0x8007CCCC,
    "kBattleNearClipConsumer": 0x80098160,
    "kBattleDynamicOtSubmit": 0x8008A3A0,
    "kProjectionDistanceWord": 0x8005E248,
    "kNearClipWord": 0x8005E0C8,
    "kViewportRectWord": 0x8005DFD4,
}

# The `config/*/splat.yaml` text-segment extent per module, so coverage is a measured number and
# not an impression. A module's text segment is `[first .c subsegment, its `data` subsegment)`.
MODULE_TEXT = {
    "BATTLE.PRG": (0x146C, 0x7F984),
    "SLUS_010.40": (0x814, 0x62000),
}


class Census:
    """One word's occurrences, split by what the decompiled line does with it."""

    def __init__(self, word):
        self.word = word
        self.writes = []
        self.reads = []
        self.declarations = []

    @property
    def total(self):
        return len(self.writes) + len(self.reads) + len(self.declarations)

    def sites(self):
        return sorted(self.writes + self.reads + self.declarations, key=lambda s: (s[0], s[1]))


def read_module_maps(paths=MODULE_MAPS):
    """address -> [names], refusing when a map that was asked for is absent."""
    table = {}
    found = []
    missing = []
    for path in paths:
        if not os.path.isfile(path):
            missing.append(path)
            continue
        found.append(path)
        with open(path, encoding="utf-8", errors="replace") as source:
            for line in source:
                match = re.match(r"\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(0x[0-9a-fA-F]+)", line)
                if match:
                    table.setdefault(int(match.group(2), 16), []).append(match.group(1))
    if missing:
        raise Refuse(
            "module map(s) absent: "
            + ", ".join(os.path.relpath(p, ROOT) for p in missing)
            + f"; read {len(found)} of {len(paths)} asked for, the missing ones were NOT read"
        )
    if not table:
        raise Refuse("every module map read but none held a `name = 0xADDR` line")
    return table


def list_sources(root=DECOMP_SRC):
    if not os.path.isdir(root):
        raise Refuse(
            f"no decompilation corpus at {os.path.relpath(root, ROOT)}; this instrument reads the "
            "vendored reconstruction and cannot answer anything without it"
        )
    found = []
    for directory, _subdirs, names in os.walk(root):
        for name in names:
            if name.endswith(SOURCE_SUFFIXES):
                found.append(os.path.join(directory, name))
    found.sort()
    if not found:
        raise Refuse(f"decompilation corpus at {os.path.relpath(root, ROOT)} held no .c/.h/.s file")
    return found


def classify(word, line):
    """WRITE / READ / DECL for one decompiled line. `extern` is a declaration, not a read."""
    if re.search(r"^\s*extern\b", line):
        return "decl"
    if re.search(re.escape(word) + r"\s*(=[^=]|\+=|-=|\*=|/=|\|=|&=|\^=|<<=|>>=)", line):
        return "write"
    return "read"


def census_word(word, sources, root=DECOMP_SRC):
    record = Census(word)
    pattern = re.compile(r"\b" + re.escape(word) + r"\b")
    line_total = 0
    for path in sources:
        relative = os.path.relpath(path, root)
        with open(path, encoding="utf-8", errors="replace") as source:
            text = source.read()
        # `split("\n")` yields a trailing empty element for text that ends in a newline, and that
        # element is not a line. Counting it would inflate every denominator this tool prints by one
        # per file, which is exactly the kind of quiet inflation a denominator exists to prevent.
        body = text[:-1] if text.endswith("\n") else text
        for number, line in enumerate(body.split("\n"), 1):
            line_total += 1
            if not pattern.search(line):
                continue
            bucket = {
                "write": record.writes,
                "read": record.reads,
                "decl": record.declarations,
            }[classify(word, line)]
            bucket.append((relative, number, line.strip()))
    record.scanned_lines = line_total
    return record


def read_shipped_addresses(paths=FACTS_HEADERS):
    """name -> address as it appears in the SHIPPING facts headers."""
    shipped = {}
    for path in paths:
        if not os.path.isfile(path):
            raise Refuse(f"shipping facts header absent: {os.path.relpath(path, ROOT)}")
        with open(path, encoding="utf-8", errors="replace") as source:
            text = source.read()
        for match in re.finditer(
            r"inline constexpr std::uint32_t (k[A-Za-z0-9_]+)\s*=\s*(0x[0-9a-fA-F]+)u?\s*;", text
        ):
            shipped[match.group(1)] = int(match.group(2), 16)
    if not shipped:
        raise Refuse("no `inline constexpr std::uint32_t kName = 0x...` constant was read")
    return shipped


def shipped_symbol_name(constant):
    """The decompilation symbol a C++ constant name refers to, when they share a name.

    A naming convention only, never the gate. The gate reads the header's DECLARED `kDecompSymbols`
    table, because comparing a shipping name against a module-map name verbatim can only ever report
    a difference (`kProjectionDistanceWord` against `vs_main_projectionDistance`), and a gate that is
    permanently red for a naming convention trains its reader to ignore it.
    """
    return constant[1:] if constant.startswith("k") else constant


def read_declared_symbols(path):
    """The `kDecompSymbols` table as [(constant name, declared decompilation symbol), ...]."""
    if not os.path.isfile(path):
        raise Refuse("shipping facts header absent: " + os.path.relpath(path, ROOT))
    with open(path, encoding="utf-8", errors="replace") as source:
        text = source.read()
    body = re.search(r"kDecompSymbols\[\]\s*=\s*\{(.*?)\n\};", text, re.S)
    if not body:
        raise Refuse("no kDecompSymbols table was read from " + os.path.relpath(path, ROOT))
    pairs = re.findall(r'\{\s*"([A-Za-z0-9_]+)"\s*,\s*"([A-Za-z0-9_]+)"\s*\}', body.group(1))
    if not pairs:
        raise Refuse("the kDecompSymbols table was read but held no {constant, symbol} pair")
    return pairs


def crosscheck_declarations(declared, shipped, table):
    """Each DECLARED (constant, symbol) pair against the module map.

    Returns (agreements, contradictions). A contradiction is a declared claim the module map does not
    support: either nothing is at that address, or something else is. That is the failure this
    instrument exists to catch -- a guessed guest address entering the tree with a name attached.
    """
    agreements = []
    contradictions = []
    for constant, symbol in declared:
        if constant not in shipped:
            contradictions.append((constant, None, symbol, ()))
            continue
        address = shipped[constant]
        names = table.get(address)
        if names and symbol in names:
            agreements.append((constant, address, symbol, tuple(names)))
        else:
            contradictions.append((constant, address, symbol, tuple(names or ())))
    return agreements, contradictions


def crosscheck_names(shipped, table):
    """Informational only: where each shipping address is corroborated by the module map, if at all.

    Never a failure. It exists so a reader can see which of this repository's addresses the
    decompilation independently names and which rest on this repository's own byte measurement alone,
    which is a distinction a reader would otherwise have to guess.
    """
    named = []
    silent = []
    for name in sorted(shipped):
        names = table.get(shipped[name])
        (named if names else silent).append((name, shipped[name], tuple(names or ())))
    return named, silent


def census(sources=None, shipped=None, table=None, declared=None):
    sources = list_sources() if sources is None else sources
    table = read_module_maps() if table is None else table
    shipped = read_shipped_addresses() if shipped is None else shipped
    declared = read_declared_symbols(FACTS_HEADERS[0]) if declared is None else declared
    records = {word: census_word(word, sources) for word in WATCHED_WORDS}
    agreements, contradictions = crosscheck_declarations(declared, shipped, table)
    named, silent = crosscheck_names(shipped, table)
    total_lines = sum(record.scanned_lines for record in records.values())
    return {
        "sources": sources,
        "records": records,
        "shipped": shipped,
        "declared": declared,
        "agreements": agreements,
        "contradictions": contradictions,
        "named": named,
        "silent": silent,
        "unique_lines": max((r.scanned_lines for r in records.values()), default=0),
        "total_lines": total_lines,
    }


def report(result, out=sys.stdout):
    sources = result["sources"]
    print("== Vagrant Story guest projection census (rood-reverse DECOMPILATION) ==", file=out)
    print(
        f"  scanned {len(sources)} decompilation source file(s), {result['unique_lines']} line(s); "
        f"{len(WATCHED_WORDS)} watched word(s), {result['total_lines']} word-line pass(es)",
        file=out,
    )
    print(
        "  this is a reading of a RECONSTRUCTION. It is not a measurement of the compiled game, and "
        "a zero below means 'no decompiled site names this word', not 'the guest has no such site'.",
        file=out,
    )
    for module, (start, end) in sorted(MODULE_TEXT.items()):
        print(
            f"  coverage note: {module} text segment is 0x{start:X}..0x{end:X} "
            f"({end - start} bytes) in the vendored tree's module map; only the decompiled part is read",
            file=out,
        )

    print("\n  -- word census: writes, reads, declarations --", file=out)
    for word in WATCHED_WORDS:
        record = result["records"][word]
        home = WORD_HOME.get(word, "any")
        print(
            f"  {word:<28} home={home:<14} total={record.total:<4} "
            f"writes={len(record.writes):<3} reads={len(record.reads):<3} decls={len(record.declarations)}",
            file=out,
        )
        for kind, sites in (("WRITE", record.writes), ("READ", record.reads)):
            for relative, number, text in sites:
                print(f"      {kind:<5} {relative}:{number}: {text[:96]}", file=out)
        if not record.writes and not record.reads:
            print(
                f"      MATCHED NONE across {result['unique_lines']} scanned line(s): no decompiled "
                f"site names {word}. This zero is a real answer about the decompilation and says "
                "nothing about the undecompiled remainder of the module.",
                file=out,
            )

    print("\n  -- DECLARED address vs the decompilation's own module map (the gate) --", file=out)
    print(
        f"  {len(result['declared'])} declaration(s) in {os.path.relpath(FACTS_HEADERS[0], ROOT)} "
        f"checked against {len(MODULE_MAPS)} module map(s): agree={len(result['agreements'])} "
        f"CONTRADICTED={len(result['contradictions'])}",
        file=out,
    )
    for name, address, symbol, names in result["agreements"]:
        print(
            f"    AGREE       {name} = 0x{address:08X} holds {symbol} (map also: "
            f"{', '.join(n for n in names if n != symbol) or 'no other name'})",
            file=out,
        )
    for name, address, symbol, names in result["contradictions"]:
        where = "no module map names anything there" if not names else f"the map names {', '.join(names)} there"
        shown = "0x???????? (the constant is not in the shipping header)" if address is None else f"0x{address:08X}"
        print(
            f"    CONTRADICTED {name} = {shown} is declared to hold {symbol}, but {where}",
            file=out,
        )

    print(
        f"\n  -- all {len(result['shipped'])} shipped address(es), ungated: corroborated by the map "
        f"at {len(result['named'])}, not named by the map at {len(result['silent'])} --",
        file=out,
    )
    print("    (informational, never a failure: an address the decompilation does not name rests on",
          file=out)
    print("     this repository's own byte measurement alone, and a reader should be told which)", file=out)
    for name, address, names in result["named"]:
        same = "same name" if shipped_symbol_name(name) in names else "different name"
        print(f"    CORROBORATED {name} = 0x{address:08X} -> {', '.join(names)} ({same})", file=out)
    for name, address, _names in result["silent"]:
        print(f"    UNNAMED     {name} = 0x{address:08X}", file=out)
    return result


def selftest():
    """The census must be able to come back negative, or its zeroes mean nothing."""
    import tempfile

    failures = []

    def require(condition, message):
        if not condition:
            failures.append(message)

    # 1. Negative corpus: a real file with none of the watched words. The census must report a
    #    genuine zero AND the report must say how much it scanned. This is the case that would be
    #    indistinguishable from "the instrument never ran" without the denominator.
    with tempfile.TemporaryDirectory() as scratch:
        fixture = os.path.join(scratch, "empty.c")
        with open(fixture, "w", encoding="utf-8") as sink:
            sink.write("int unrelated(void) { return 0; }\n" * 5)
        empty = census_word("vs_main_projectionDistance", [fixture])
        require(empty.total == 0, f"negative corpus matched {empty.total} occurrence(s), expected 0")
        require(
            empty.scanned_lines == 5,
            f"negative corpus reported {empty.scanned_lines} scanned line(s), expected 5",
        )

    # 2. Positive control: the same instrument on a corpus that DOES name the word must find it,
    #    and must classify a write as a write and an extern as a declaration. Without this, a zero
    #    could equally mean the classifier never fires.
    with tempfile.TemporaryDirectory() as scratch:
        fixture = os.path.join(scratch, "positive.c")
        with open(fixture, "w", encoding="utf-8") as sink:
            sink.write("extern int vs_main_projectionDistance;\n")
            sink.write("vs_main_projectionDistance = 0x100;\n")
            sink.write("if (vs_main_projectionDistance < 272) { x(); }\n")
            sink.write("vs_main_projectionDistance += 0x40;\n")
        record = census_word("vs_main_projectionDistance", [fixture])
        require(
            len(record.declarations) == 1,
            f"extern classified as {len(record.declarations)} declaration(s), expected 1",
        )
        require(
            len(record.writes) == 2,
            f"assignment and += classified as {len(record.writes)} write(s), expected 2",
        )
        require(
            len(record.reads) == 1,
            f"comparison classified as {len(record.reads)} read(s), expected 1",
        )

    # 3. The gate must fire. A declared (constant, symbol) pair the module map does not support is
    #    exactly a guessed guest address entering the tree with a name attached, and a gate that
    #    cannot come back red proves nothing when it comes back green. Two shapes must both fail: a
    #    name the map does not have at that address, and an address the map says nothing about.
    table = {0x80041540: ["SetGeomOffset"], 0x80041544: ["SetGeomScreen"]}
    shipped = {"kSetGeomOffset": 0x80041540, "kWrong": 0x80041544, "kSilent": 0x80099999}
    declared = [("kSetGeomOffset", "SetGeomOffset"), ("kWrong", "SetGeomOffset"), ("kSilent", "Something")]
    agreements, contradictions = crosscheck_declarations(declared, shipped, table)
    require(len(agreements) == 1, f"the gate reported {len(agreements)} agreement(s), expected 1")
    require(
        len(contradictions) == 2,
        f"the gate reported {len(contradictions)} contradiction(s) for a wrong name and a silent "
        f"address, expected 2",
    )
    blamed = {name for name, _address, _symbol, _names in contradictions}
    require(
        blamed == {"kWrong", "kSilent"},
        f"the gate blamed {sorted(blamed)} for the contradictions, expected kWrong and kSilent",
    )

    # 4. A declaration naming a constant the shipping header does not define must also fail, rather
    #    than being skipped: a typo in the table is exactly how a real address would stop being gated.
    _agreements, typo = crosscheck_declarations([("kTypo", "SetGeomOffset")], shipped, table)
    require(len(typo) == 1, "a declaration naming an undefined constant must be a contradiction")

    # 5. The ungated informational pass must separate corroborated addresses from unnamed ones, and
    #    must not fail on either.
    named, silent = crosscheck_names(shipped, table)
    require(len(named) == 2, f"the informational pass named {len(named)} address(es), expected 2")
    require(len(silent) == 1, f"the informational pass left {len(silent)} address(es) unnamed, expected 1")

    # 6. A missing corpus must refuse, naming what it could not read.
    try:
        list_sources(os.path.join(ROOT, "external", "rood-reverse", "src-does-not-exist"))
        failures.append("a missing decompilation corpus was answered instead of refused")
    except Refuse as error:
        require(
            "src-does-not-exist" in str(error),
            f"the missing-corpus refusal did not name the missing path: {error}",
        )

    # 7. A missing module map must refuse AND declare itself short, never answer with an empty table.
    try:
        read_module_maps([os.path.join(ROOT, "no-such-module-map.txt")])
        failures.append("a missing module map was answered instead of refused")
    except Refuse as error:
        require(
            "0 of 1" in str(error) and "NOT read" in str(error),
            f"the missing-map refusal did not declare itself short: {error}",
        )

    if failures:
        for failure in failures:
            print(f"  [FAIL] {failure}")
        return 1
    print(
        "  [ ok ] 7/7 selftest cases: negative census reports a denominator, positive control "
        "classifies write/read/decl, the declared-address gate fires on a wrong name, a silent "
        "address and an undefined constant, the ungated pass separates corroborated from unnamed, and "
        "a missing corpus or module map refuses"
    )
    return 0


def main(argv):
    args = [a for a in argv if a not in ("--selftest",)]
    if "--selftest" in argv:
        if args:
            print("usage: re_projection.py [--selftest]", file=sys.stderr)
            return 2
        return selftest()
    if args:
        print("usage: re_projection.py [--selftest]", file=sys.stderr)
        return 2
    try:
        result = report(census())
    except Refuse as error:
        print(f"REFUSED: {error}", file=sys.stderr)
        return 2
    if result["contradictions"]:
        print(
            "FAILED: a DECLARED address does not hold the decompilation symbol the shipping header "
            "claims for it, so a guessed guest address may have entered the tree",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
