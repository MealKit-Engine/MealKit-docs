# MealKit docs build/checks (shared by Windows/Linux, local and CI).
#
#   python tools/build.py html                 English/Korean HTML (_build/html/en, _build/html/ko), warnings = errors
#   python tools/build.py update               updates translation files (.po) after the source changes (new sentences blank, changed sentences fuzzy)
#   python tools/build.py check [--engine DIR] html + translation checks (0 untranslated/fuzzy/leftover) + engine version comparison
#                                              + cookbook code compared with the sample files it comes from
#   python tools/build.py linkcheck            external link checks (network)

import argparse
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(ROOT, "_build")
LANGUAGES = ["ko"]


def sphinx(builder, out, *extra):
    cmd = [sys.executable, "-m", "sphinx", "-b", builder, "-W", "--keep-going", "-q", "-E", ROOT, out, *extra]
    print("+", " ".join(cmd[2:]), flush=True)
    if subprocess.call(cmd) != 0:
        sys.exit(f"FAIL: sphinx {builder} {' '.join(extra)}")


def gettext():
    out = os.path.join(BUILD, "gettext")
    shutil.rmtree(out, ignore_errors=True)
    sphinx("gettext", out)
    return out


def html():
    sphinx("html", os.path.join(BUILD, "html", "en"))
    for lang in LANGUAGES:
        sphinx("html", os.path.join(BUILD, "html", lang), "-D", f"language={lang}")
    print("html: _build/html/en/index.html, " + ", ".join(f"_build/html/{l}/index.html" for l in LANGUAGES))


def update():
    pot = gettext()
    cmd = [sys.executable, "-m", "sphinx_intl", "update", "-p", pot, "-d", os.path.join(ROOT, "locale"),
           "--line-width", "-1", "--no-obsolete"]
    for lang in LANGUAGES:
        cmd += ["-l", lang]
    if subprocess.call(cmd) != 0:
        sys.exit("FAIL: sphinx-intl update")


def read_catalog(path):
    from babel.messages.pofile import read_po

    with open(path, "rb") as f:
        return read_po(f)


def check_translations():
    """Whether every source sentence is translated in each language (no blanks/fuzzy), and no translations remain that aren't in the source."""
    pot_dir = gettext()
    problems = 0
    for lang in LANGUAGES:
        total = 0
        for dirpath, _, files in os.walk(pot_dir):
            for name in sorted(files):
                if not name.endswith(".pot"):
                    continue
                pot_path = os.path.join(dirpath, name)
                rel = os.path.relpath(pot_path, pot_dir)[:-4]
                po_path = os.path.join(ROOT, "locale", lang, "LC_MESSAGES", rel + ".po")
                pot = read_catalog(pot_path)
                if not os.path.exists(po_path):
                    print(f"{lang}/{rel}.po: missing (run: python tools/build.py update)")
                    problems += 1
                    continue
                po = read_catalog(po_path)
                ids = set()
                for msg in pot:
                    if not msg.id:
                        continue
                    ids.add(msg.id)
                    total += 1
                    tr = po.get(msg.id)
                    if tr is None or not tr.string:
                        print(f"{lang}/{rel}.po: untranslated: {msg.id[:70]!r}")
                        problems += 1
                    elif tr.fuzzy:
                        print(f"{lang}/{rel}.po: fuzzy: {msg.id[:70]!r}")
                        problems += 1
                for msg in po:
                    if msg.id and msg.id not in ids:
                        print(f"{lang}/{rel}.po: obsolete (not in source): {msg.id[:70]!r}")
                        problems += 1
                problems += len(po.obsolete)
        print(f"translations {lang}: {total} messages checked")
    # Translation files whose source is gone
    for lang in LANGUAGES:
        base = os.path.join(ROOT, "locale", lang, "LC_MESSAGES")
        for dirpath, _, files in os.walk(base):
            for name in files:
                if name.endswith(".po"):
                    rel = os.path.relpath(os.path.join(dirpath, name), base)[:-3]
                    if not os.path.exists(os.path.join(pot_dir, rel + ".pot")):
                        print(f"{lang}/{rel}.po: no source document")
                        problems += 1
    return problems


def check_engine_version(engine_dir):
    with open(os.path.join(ROOT, "ENGINE_VERSION"), encoding="utf-8") as f:
        docs = f.read().strip()
    parts = docs.split(".")
    if len(parts) != 2 or not all(p.isdigit() for p in parts):
        print(f"ENGINE_VERSION: '{docs}' is not MAJOR.MINOR")
        return 1
    if not engine_dir:
        print(f"engine version: {docs} (no --engine given, not compared)")
        return 0
    with open(os.path.join(engine_dir, "VERSION"), encoding="utf-8") as f:
        engine = f.read().strip()
    minor = ".".join(engine.split(".")[:2])
    if minor != docs:
        print(f"ENGINE_VERSION {docs} does not match engine VERSION {engine} (MINOR {minor})")
        return 1
    print(f"engine version: docs {docs} = engine {engine}")
    return 0


# Cookbook code comes from the reference samples: a "% from: <engine path>" line right before a code block names the file,
# and every non-empty line of the block must still be a line of that file (ROADMAP "Cookbook docs": it breaks visibly when the sample changes)
def check_cookbook(engine_dir):
    if not engine_dir:
        print("cookbook: no --engine given, code not compared with the samples")
        return 0
    problems = blocks = 0
    folder = os.path.join(ROOT, "cookbook")
    for name in sorted(os.listdir(folder)):
        if not name.endswith(".md"):
            continue
        with open(os.path.join(folder, name), encoding="utf-8") as f:
            lines = f.read().splitlines()
        i = 0
        while i < len(lines):
            if not lines[i].startswith("% from: "):
                i += 1
                continue
            source = lines[i][len("% from: "):].strip()
            if i + 1 >= len(lines) or not lines[i + 1].startswith("```"):
                print(f"cookbook/{name}:{i + 1}: '% from:' is not right before a code block")
                problems += 1
                i += 1
                continue
            end = i + 2
            while end < len(lines) and not lines[end].startswith("```"):
                end += 1
            path = os.path.join(engine_dir, source)
            if not os.path.exists(path):
                print(f"cookbook/{name}:{i + 1}: {source} does not exist in the engine")
                problems += 1
            else:
                with open(path, encoding="utf-8") as f:
                    have = {l.strip() for l in f.read().splitlines()}
                for k in range(i + 2, end):
                    if lines[k].strip() and lines[k].strip() not in have:
                        print(f"cookbook/{name}:{k + 1}: not in {source}: {lines[k].strip()}")
                        problems += 1
            blocks += 1
            i = end + 1
    print(f"cookbook: {blocks} code block(s) compared with the samples")
    return problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=["html", "update", "check", "linkcheck", "gettext"])
    ap.add_argument("--engine", help="engine repository folder (compares VERSION MINOR)")
    args = ap.parse_args()
    os.chdir(ROOT)
    if args.command == "html":
        html()
    elif args.command == "update":
        update()
    elif args.command == "gettext":
        gettext()
    elif args.command == "linkcheck":
        sphinx("linkcheck", os.path.join(BUILD, "linkcheck"))
    elif args.command == "check":
        html()
        problems = check_translations() + check_engine_version(args.engine) + check_cookbook(args.engine)
        if problems:
            sys.exit(f"FAIL: {problems} problem(s)")
        print("PASS")


if __name__ == "__main__":
    main()
