"""Packaging round (WP4c) — the Inno Setup script and its generated version
header describe the installer the user ships.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
ISS = PROJECT_ROOT / "packaging" / "windows_installer.iss"
VERSION_ISS = PROJECT_ROOT / "packaging" / "version.iss"
GEN = PROJECT_ROOT / "tools" / "gen_version_iss.py"


def _iss() -> str:
    return ISS.read_text(encoding="utf-8")


def _pyproject_version() -> str:
    text = (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*"([^"]+)"', text, re.M)
    assert match, "pyproject.toml has no [project].version"
    return match.group(1)


def test_the_version_comes_from_the_generated_header():
    text = _iss()
    assert '#include "version.iss"' in text
    assert "AppVersion={#AppVersion}" in text
    assert not re.search(r"^AppVersion=\d", text, re.M), "hardcoded AppVersion"
    assert VERSION_ISS.is_file()
    assert f'#define AppVersion "{_pyproject_version()}"' in VERSION_ISS.read_text(encoding="utf-8")


def test_the_generator_writes_the_pyproject_version(tmp_path):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "x"\nversion = "9.8.7"\n', encoding="utf-8")
    out = tmp_path / "version.iss"
    proc = subprocess.run(
        [sys.executable, str(GEN), "--pyproject", str(pyproject), "--out", str(out)],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    assert out.read_text(encoding="utf-8").strip() == '#define AppVersion "9.8.7"'


def test_installer_targets_64_bit_and_lets_the_user_pick_the_privilege_level():
    text = _iss()
    assert "ArchitecturesInstallIn64BitMode=x64compatible" in text
    assert "ArchitecturesAllowed=x64compatible" in text
    assert "PrivilegesRequiredOverridesAllowed=dialog" in text
    assert "UninstallDisplayIcon={app}\\Macena_CS2_Analyzer.exe" in text


def test_uninstall_asks_before_removing_the_user_data_folder():
    text = _iss()
    assert "CurUninstallStepChanged" in text
    assert "{localappdata}\\MacenaCS2Analyzer" in text
    assert "DelTree(" in text
    assert re.search(r"MsgBox\([^;]*mbConfirmation", text, re.S)


_ISPP_DIRECTIVES = {
    "#include",
    "#define",
    "#ifexist",
    "#ifnexist",
    "#if",
    "#ifdef",
    "#ifndef",
    "#else",
    "#elif",
    "#endif",
    "#pragma",
    "#error",
}


def test_no_code_line_starts_with_a_hash_that_ispp_would_read_as_a_directive():
    # ISCC 6.7.3: a [Code] continuation line beginning with `#13#10` aborts the
    # compile with "Unknown preprocessor directive" (line 90 of the first build).
    for number, line in enumerate(_iss().splitlines(), 1):
        stripped = line.strip()
        if stripped.startswith("#"):
            word = stripped.split()[0]
            assert word in _ISPP_DIRECTIVES, f"line {number}: {stripped[:40]!r}"


def test_the_dist_folder_is_a_preprocessor_parameter_for_short_build_paths():
    # torch's nested license files sit 182 characters below the dist root;
    # from a long checkout path they pass 260 and ISCC aborts with "The system
    # cannot find the path specified". The build script therefore builds into
    # a short folder and passes it as /DDistDir; the default stays ..\dist.
    text = _iss()
    assert "#ifndef DistDir" in text
    assert '#define DistDir "..\\dist"' in text
    assert 'Source: "{#DistDir}\\Macena_CS2_Analyzer\\*"' in text
    assert 'Source: "..\\dist\\Macena_CS2_Analyzer\\*"' not in text


def test_no_dem_file_association_and_the_redist_is_optional():
    text = _iss()
    assert ".dem" not in text
    assert "#ifexist" in text and "vc_redist.x64.exe" in text


def test_lessons_from_the_first_compiled_installer():
    text = _iss()
    # One self-contained exe: the first compile shipped a separate 457 MB
    # "-1.bin" slice that a user could forget to copy.
    assert re.search(r"^DiskSpanning=no", text, re.M)
    assert "DiskClusterSize" not in text
    # ISCC warning: {userdesktop} under PrivilegesRequired=admin puts the icon
    # on the administrator's desktop; {autodesktop} follows the install mode.
    assert "{userdesktop}" not in text and "{autodesktop}" in text
    # The VC++ redistributable needs elevation: run it only in an admin install
    # (a per-user install cannot elevate and the first smoke stalled on it).
    for line in text.splitlines():
        if "vc_redist.x64.exe" in line and line.startswith(("Source:", "Filename:")):
            assert "IsAdminInstallMode" in line, line
