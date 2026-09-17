#!/usr/bin/env python3
"""Turn an upstream Citron checkout into the Simplified Chinese build.

Three things happen here:

1. Localisation  - the bundled zh_CN translation is compiled to a .qm and embedded through a
                   plain Qt resource file, so the build never needs Qt's LinguistTools (which the
                   cross-compile toolchain does not ship). Simplified Chinese also becomes the
                   default UI language.
2. Cheat manager - a standalone cheat dialog is added to the Tools menu, letting the user tick
                   exactly which cheats run and hot-reloading the cheat engine while a game runs.
3. Cheat master  - a global "cheats_enabled" setting gates the whole cheat engine.

Every edit is anchored on an exact snippet of upstream source. A missing or ambiguous anchor is a
hard error: a silently skipped patch would produce an English build that looks fine in CI.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


class PatchError(RuntimeError):
    pass


class Patcher:
    def __init__(self, citron: Path) -> None:
        self.citron = citron
        self.applied: list[str] = []
        self.skipped: list[str] = []

    # -- helpers ---------------------------------------------------------------------------
    def _read(self, rel: str) -> str:
        path = self.citron / rel
        if not path.is_file():
            raise PatchError(f"missing source file: {rel}")
        return path.read_text(encoding="utf-8")

    def _write(self, rel: str, text: str) -> None:
        (self.citron / rel).write_text(text, encoding="utf-8")

    def replace(self, rel: str, anchor: str, replacement: str, *, marker: str, what: str) -> None:
        """Replace `anchor` with `replacement` in `rel`, exactly once.

        `marker` is a string that only exists after the patch; finding it means the tree was
        already patched and the edit is skipped instead of applied twice.
        """
        text = self._read(rel)
        if marker in text:
            self.skipped.append(f"{what} (already patched)")
            return
        occurrences = text.count(anchor)
        if occurrences != 1:
            raise PatchError(
                f"{what}: expected exactly 1 anchor match in {rel}, found {occurrences}.\n"
                f"Upstream changed; update the anchor in tools/patch_citron.py.\n"
                f"--- anchor ---\n{anchor}\n--------------"
            )
        self._write(rel, text.replace(anchor, replacement, 1))
        self.applied.append(what)

    def insert_after(self, rel: str, anchor: str, addition: str, *, marker: str, what: str) -> None:
        self.replace(rel, anchor, anchor + addition, marker=marker, what=what)

    def insert_before(self, rel: str, anchor: str, addition: str, *, marker: str, what: str) -> None:
        self.replace(rel, anchor, addition + anchor, marker=marker, what=what)

    def copy(self, src: Path, rel: str, *, what: str) -> None:
        dest = self.citron / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dest)
        self.applied.append(what)

    # -- 1. localisation -------------------------------------------------------------------
    def build_qm(self) -> Path:
        """Compile translations/zh_CN.ts to a .qm, falling back to the committed binary."""
        ts = REPO / "translations" / "zh_CN.ts"
        if not ts.is_file():
            raise PatchError("translations/zh_CN.ts is missing")

        committed_qm = REPO / "translations" / "zh_CN.qm"
        out = Path(tempfile.mkdtemp(prefix="citron-zh-")) / "zh_CN.qm"

        lrelease = shutil.which("lrelease-qt6") or shutil.which("lrelease") or (
            "/usr/lib/qt6/bin/lrelease" if Path("/usr/lib/qt6/bin/lrelease").is_file() else None
        )
        if lrelease:
            result = subprocess.run(
                [lrelease, str(ts), "-qm", str(out)], capture_output=True, text=True
            )
            if result.returncode == 0 and out.is_file() and out.stat().st_size > 1024:
                print(f"  compiled zh_CN.qm with {lrelease} ({out.stat().st_size} bytes)")
                return out
            print(f"  lrelease failed ({result.returncode}): {result.stderr.strip()[:400]}")

        if committed_qm.is_file() and committed_qm.stat().st_size > 1024:
            print(f"  using committed zh_CN.qm ({committed_qm.stat().st_size} bytes)")
            return committed_qm

        raise PatchError(
            "could not produce zh_CN.qm: lrelease is unavailable and no usable "
            "translations/zh_CN.qm is committed"
        )

    def patch_translations(self) -> None:
        qm = self.build_qm()

        # Keep the .ts next to upstream's own bundle so anyone enabling ENABLE_QT_TRANSLATION by
        # hand still picks up the complete translation.
        self.copy(REPO / "translations" / "zh_CN.ts", "dist/languages/zh_CN.ts", what="zh_CN.ts bundle")

        # Embed the compiled catalogue through AUTORCC. Upstream's own translation path needs
        # Qt6::lrelease, which the llvm-mingw cross toolchain does not provide; a plain .qrc only
        # needs rcc, which every Qt build ships.
        self.copy(qm, "src/citron/zh_CN.qm", what="zh_CN.qm resource")
        self._write(
            "src/citron/translations_zh.qrc",
            '<RCC>\n  <qresource prefix="languages">\n    <file>zh_CN.qm</file>\n'
            "  </qresource>\n</RCC>\n",
        )
        self.applied.append("translations_zh.qrc")

    # -- 2. default language ---------------------------------------------------------------
    def patch_default_language(self) -> None:
        self.replace(
            "src/citron/uisettings.h",
            'Setting<std::string> language{linkage, {}, "language", Category::Paths};',
            'Setting<std::string> language{linkage, std::string("zh_CN"), "language", '
            "Category::Paths};",
            marker='language{linkage, std::string("zh_CN")',
            what="default UI language -> zh_CN",
        )

        # When the requested locale has no catalogue, prefer Chinese over English: this build
        # exists to be Chinese, and an unknown locale should not silently land in English.
        self.replace(
            "src/citron/main.cpp",
            """    if (loaded) {
        qApp->installTranslator(&translator);
    } else {
        UISettings::values.language = std::string("en");
    }""",
            """    if (loaded) {
        qApp->installTranslator(&translator);
    } else if (translator.load(QStringLiteral("zh_CN"), QStringLiteral(":/languages/"))) {
        // Chinese build: fall back to Simplified Chinese before giving up on translation.
        UISettings::values.language = std::string("zh_CN");
        qApp->installTranslator(&translator);
    } else {
        UISettings::values.language = std::string("en");
    }""",
            marker="Chinese build: fall back to Simplified Chinese",
            what="translation fallback -> zh_CN",
        )

    # -- 3. cheat engine master switch -----------------------------------------------------
    def patch_cheat_setting(self) -> None:
        self.replace(
            "src/common/settings.h",
            """    // Cheats
    // Key: build_id (hex string), Value: set of disabled cheat names
    std::map<std::string, std::set<std::string>> disabled_cheats;""",
            """    // Cheats
    // Master switch for the cheat engine. Individual cheats stay selected while this is off.
    Setting<bool> cheats_enabled{linkage, true, "cheats_enabled", Category::Core};
    // Key: build_id (hex string), Value: set of disabled cheat names
    std::map<std::string, std::set<std::string>> disabled_cheats;""",
            marker='cheats_enabled{linkage, true, "cheats_enabled"',
            what="Settings::values.cheats_enabled",
        )

        # Gate the list the engine actually runs, not ApplyDisabledCheats: that helper also backs
        # PatchManager::GetCheats(), which the cheat manager reads to show which cheats the user
        # picked. Flattening it there would make every tick disappear while the master is off.
        # Blanking `enabled` instead of returning an empty list matters too - the loader only
        # registers a cheat engine for a non-empty list, and without one the master switch could
        # not be flipped back on mid-game.
        self.replace(
            "src/core/file_sys/patch_manager.cpp",
            """                std::copy(cheats.begin(), cheats.end(), std::back_inserter(out));
            }
        }
    }
    return out;
}""",
            """                std::copy(cheats.begin(), cheats.end(), std::back_inserter(out));
            }
        }
    }

    if (!Settings::values.cheats_enabled.GetValue()) {
        // Master switch off: keep the entries so the engine still gets registered and can be
        // hot-reloaded, but let none of them run.
        for (auto& cheat : out) {
            cheat.enabled = false;
        }
    }

    return out;
}""",
            marker="Master switch off: keep the entries",
            what="global cheat gate in CreateCheatList",
        )

        self.replace(
            "src/citron/configuration/shared_translation.cpp",
            "    INSERT(Settings, use_speed_limit, QStringLiteral(), QStringLiteral());",
            """    INSERT(Settings, cheats_enabled, tr("Enable cheats"),
           tr("Master switch for the cheat engine.\\n"
              "Turn it off to suspend every cheat without losing which ones you picked.\\n"
              "Pick individual cheats from Tools > Cheat Manager."));
    INSERT(Settings, use_speed_limit, QStringLiteral(), QStringLiteral());""",
            marker="INSERT(Settings, cheats_enabled",
            what="cheats_enabled settings label",
        )

    # -- 4. cheat manager dialog -----------------------------------------------------------
    def patch_cheat_manager(self) -> None:
        src = REPO / "patches" / "src" / "citron"
        self.copy(src / "cheat_manager_dialog.h", "src/citron/cheat_manager_dialog.h",
                  what="cheat_manager_dialog.h")
        self.copy(src / "cheat_manager_dialog.cpp", "src/citron/cheat_manager_dialog.cpp",
                  what="cheat_manager_dialog.cpp")

        self.insert_before(
            "src/citron/CMakeLists.txt",
            "    main.cpp\n    main.h\n    main.ui\n",
            "    cheat_manager_dialog.cpp\n    cheat_manager_dialog.h\n    translations_zh.qrc\n",
            marker="cheat_manager_dialog.cpp",
            what="CMake sources",
        )

        # Menu entry
        self.replace(
            "src/citron/main.ui",
            '    <addaction name="action_Capture_Screenshot"/>\n    <addaction name="menuTAS"/>',
            '    <addaction name="action_Capture_Screenshot"/>\n'
            '    <addaction name="separator"/>\n'
            '    <addaction name="action_Cheat_Manager"/>\n'
            '    <addaction name="menuTAS"/>',
            marker='<addaction name="action_Cheat_Manager"/>',
            what="Tools menu entry",
        )
        self.insert_before(
            "src/citron/main.ui",
            " </widget>\n <resources>\n  <include location=\"citron.qrc\"/>",
            '  <action name="action_Cheat_Manager">\n'
            '   <property name="text">\n'
            "    <string>Cheat &amp;Manager</string>\n"
            "   </property>\n"
            '   <property name="toolTip">\n'
            "    <string>Choose which cheats run for the game you are playing</string>\n"
            "   </property>\n"
            "  </action>\n",
            marker='<action name="action_Cheat_Manager">',
            what="Tools menu action",
        )

        # Slot declaration
        self.replace(
            "src/citron/main.h",
            "    void OnCaptureScreenshot();",
            "    void OnCaptureScreenshot();\n    void OnOpenCheatManager();",
            marker="OnOpenCheatManager",
            what="GMainWindow::OnOpenCheatManager declaration",
        )

        # Include, wiring and implementation
        self.replace(
            "src/citron/main.cpp",
            '#include "citron/bootmanager.h"',
            '#include "citron/bootmanager.h"\n#include "citron/cheat_manager_dialog.h"',
            marker='#include "citron/cheat_manager_dialog.h"',
            what="main.cpp include",
        )
        self.replace(
            "src/citron/main.cpp",
            "    connect_menu(ui->action_Capture_Screenshot, &GMainWindow::OnCaptureScreenshot);",
            "    connect_menu(ui->action_Capture_Screenshot, &GMainWindow::OnCaptureScreenshot);\n"
            "    connect_menu(ui->action_Cheat_Manager, &GMainWindow::OnOpenCheatManager);",
            marker="action_Cheat_Manager, &GMainWindow::OnOpenCheatManager",
            what="main.cpp menu wiring",
        )
        self.replace(
            "src/citron/main.cpp",
            "void GMainWindow::OnConfigurePerGame() {",
            """void GMainWindow::OnOpenCheatManager() {
    if (!system->IsPoweredOn()) {
        QMessageBox::information(
            this, tr("Cheat Manager"),
            tr("Start a game first.\\n\\nCheats for a game that is not running can be picked in "
               "its right-click menu, under Properties > Cheats."));
        return;
    }

    CheatManagerDialog dialog(*system, system->GetApplicationProcessProgramID(), this);
    dialog.exec();
}

void GMainWindow::OnConfigurePerGame() {""",
            marker="void GMainWindow::OnOpenCheatManager()",
            what="main.cpp OnOpenCheatManager implementation",
        )

    # -- verification ----------------------------------------------------------------------
    def verify(self) -> None:
        checks = [
            ("src/citron/zh_CN.qm", None),
            ("src/citron/translations_zh.qrc", "zh_CN.qm"),
            ("src/citron/cheat_manager_dialog.cpp", "CheatManagerDialog::RefreshCheats"),
            ("src/citron/cheat_manager_dialog.h", "class CheatManagerDialog"),
            ("src/citron/CMakeLists.txt", "cheat_manager_dialog.cpp"),
            ("src/citron/CMakeLists.txt", "translations_zh.qrc"),
            ("src/citron/uisettings.h", 'language{linkage, std::string("zh_CN")'),
            ("src/citron/main.cpp", "Chinese build: fall back to Simplified Chinese"),
            ("src/citron/main.cpp", '#include "citron/cheat_manager_dialog.h"'),
            ("src/citron/main.cpp", "void GMainWindow::OnOpenCheatManager()"),
            ("src/citron/main.h", "OnOpenCheatManager"),
            ("src/citron/main.ui", 'action name="action_Cheat_Manager"'),
            ("src/common/settings.h", 'cheats_enabled{linkage, true'),
            ("src/core/file_sys/patch_manager.cpp", "Master switch off: keep the entries"),
            ("src/citron/configuration/shared_translation.cpp", "INSERT(Settings, cheats_enabled"),
            ("dist/languages/zh_CN.ts", "<TS "),
        ]
        failures = []
        for rel, needle in checks:
            path = self.citron / rel
            if not path.is_file():
                failures.append(f"missing {rel}")
                continue
            if needle is None:
                if path.stat().st_size < 1024:
                    failures.append(f"{rel} is suspiciously small ({path.stat().st_size} bytes)")
                continue
            if needle not in path.read_text(encoding="utf-8"):
                failures.append(f"{rel} does not contain {needle!r}")
        if failures:
            raise PatchError("verification failed:\n  - " + "\n  - ".join(failures))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("citron", nargs="?", default="./citron",
                        help="path to the Citron source checkout (default: ./citron)")
    args = parser.parse_args()

    citron = Path(args.citron).resolve()
    if not (citron / "src" / "citron" / "main.cpp").is_file():
        print(f"error: {citron} does not look like a Citron checkout", file=sys.stderr)
        return 1

    print(f"=== Citron Chinese build patch ===\nsource: {citron}")
    patcher = Patcher(citron)
    try:
        print("\n[1/4] translations")
        patcher.patch_translations()
        print("\n[2/4] default language")
        patcher.patch_default_language()
        print("\n[3/4] cheat engine master switch")
        patcher.patch_cheat_setting()
        print("\n[4/4] cheat manager dialog")
        patcher.patch_cheat_manager()
        print("\n[verify]")
        patcher.verify()
    except PatchError as error:
        print(f"\nPATCH FAILED: {error}", file=sys.stderr)
        return 1

    print("\napplied:")
    for item in patcher.applied:
        print(f"  + {item}")
    for item in patcher.skipped:
        print(f"  = {item}")
    print("\n=== patch complete ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
