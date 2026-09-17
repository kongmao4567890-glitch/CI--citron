#!/usr/bin/env python3
"""Gate the build on a complete Chinese translation.

Run against a patched Citron checkout. It fails when:
  * any string the Qt frontend can show is missing a Chinese translation, or
  * the compiled catalogue is not actually embedded in the build.

Regenerating the catalogue needs lupdate; when it is unavailable the check falls back to auditing
the committed .ts on its own, which still catches an incomplete translation, just not one that has
drifted behind new upstream strings.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def find_tool(*names: str) -> str | None:
    for name in names:
        found = shutil.which(name)
        if found:
            return found
    for name in names:
        candidate = Path("/usr/lib/qt6/bin") / name
        if candidate.is_file():
            return str(candidate)
    return None


def audit(ts_path: Path) -> tuple[int, list[tuple[str, str]]]:
    """Return (live message count, [(context, source)] that have no translation)."""
    tree = ET.parse(ts_path)
    live = 0
    missing: list[tuple[str, str]] = []
    for context in tree.getroot().findall("context"):
        name = context.findtext("name") or "?"
        for message in context.findall("message"):
            translation = message.find("translation")
            if translation is None:
                continue
            # Obsolete entries keep old work around for when upstream brings a string back;
            # they are never shown, so they do not count either way.
            if translation.get("type") in ("vanished", "obsolete"):
                continue
            live += 1
            source = message.findtext("source") or ""
            forms = translation.findall("numerusform")
            if forms:
                if not any((form.text or "").strip() for form in forms):
                    missing.append((name, source))
            elif not (translation.text or "").strip():
                missing.append((name, source))
    return live, missing


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("citron", nargs="?", default="./citron",
                        help="path to the patched Citron checkout")
    parser.add_argument("--strict-refresh", action="store_true",
                        help="fail instead of warning when lupdate is unavailable")
    parser.add_argument("--write", action="store_true",
                        help="write the refreshed catalogue back to translations/zh_CN.ts so new "
                             "upstream strings can be translated (maintenance, not CI)")
    args = parser.parse_args()

    citron = Path(args.citron).resolve()
    ts = REPO / "translations" / "zh_CN.ts"
    if not ts.is_file():
        print("error: translations/zh_CN.ts is missing", file=sys.stderr)
        return 1

    # The patch must have landed, otherwise the binary ships without the catalogue.
    for rel in ("src/citron/zh_CN.qm", "src/citron/translations_zh.qrc"):
        if not (citron / rel).is_file():
            print(f"error: {rel} missing — run tools/patch_citron.py first", file=sys.stderr)
            return 1
    cmake = (citron / "src/citron/CMakeLists.txt").read_text(encoding="utf-8")
    if "translations_zh.qrc" not in cmake:
        print("error: translations_zh.qrc is not in the citron target sources", file=sys.stderr)
        return 1

    check_ts = ts
    lupdate = find_tool("lupdate-qt6", "lupdate")
    if lupdate:
        workdir = Path(tempfile.mkdtemp(prefix="citron-l10n-"))
        check_ts = workdir / "zh_CN.ts"
        shutil.copyfile(ts, check_ts)
        sources = sorted(
            str(path.relative_to(citron / "src/citron"))
            for path in (citron / "src/citron").rglob("*")
            if path.suffix in (".cpp", ".h", ".ui")
        )
        result = subprocess.run(
            [lupdate, "-locations", "none", "-target-language", "zh_CN",
             *sources, "-ts", str(check_ts)],
            cwd=citron / "src/citron", capture_output=True, text=True,
        )
        if result.returncode != 0:
            print(f"error: lupdate failed\n{result.stderr[-2000:]}", file=sys.stderr)
            return 1
        print(f"refreshed against {len(sources)} frontend source files")
    else:
        message = "lupdate not found — auditing the committed catalogue without refreshing it"
        if args.strict_refresh:
            print(f"error: {message}", file=sys.stderr)
            return 1
        print(f"warning: {message}")

    if args.write:
        if check_ts == ts:
            print("error: --write needs lupdate to refresh the catalogue first", file=sys.stderr)
            return 1
        lconvert = find_tool("lconvert-qt6", "lconvert")
        if lconvert:
            subprocess.run([lconvert, "-locations", "none", "-i", str(check_ts), "-o", str(ts)],
                           check=True)
        else:
            shutil.copyfile(check_ts, ts)
        print(f"wrote refreshed catalogue to {ts}")
        check_ts = ts

    live, missing = audit(check_ts)
    print(f"translatable strings: {live}")
    print(f"missing translations: {len(missing)}")
    if missing:
        for context, source in missing[:40]:
            print(f"  [{context}] {source[:100]!r}")
        if len(missing) > 40:
            print(f"  ... and {len(missing) - 40} more")
        print("\nTranslation is incomplete. Run this with --write, fill the new entries in "
              "translations/zh_CN.ts, then re-run.", file=sys.stderr)
        return 1

    print("translation coverage: 100%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
