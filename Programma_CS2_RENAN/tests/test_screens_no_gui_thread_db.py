"""F-0038 regression: no screen method touches the DB on the GUI thread.

The three breach sites (profile _save, tactical chronovisor wiring,
wizard _finish) now run their DB work through Worker(QRunnable). This
suite pins the split structurally AND behaviorally:
- the extracted DB functions are staticmethods (no widget access), and
- the GUI-side methods no longer contain get_db_manager references.
"""

import ast
import inspect
import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_SCREENS = Path(__file__).resolve().parents[1] / "apps" / "qt_app" / "screens"


def _method_source(cls, name):
    return inspect.getsource(getattr(cls, name))


def test_profile_save_is_split():
    from Programma_CS2_RENAN.apps.qt_app.screens.profile_screen import ProfileScreen

    gui_src = _method_source(ProfileScreen, "_save")
    assert "get_db_manager" not in gui_src, "_save touches the DB on the GUI thread"
    assert "Worker(" in gui_src
    assert isinstance(inspect.getattr_static(ProfileScreen, "_ensure_profile_row"), staticmethod)


def test_wizard_finish_is_split():
    from Programma_CS2_RENAN.apps.qt_app.screens.wizard_screen import WizardScreen

    gui_src = _method_source(WizardScreen, "_finish")
    assert "get_db_manager" not in gui_src, "_finish touches the DB on the GUI thread"
    assert "Worker(" in gui_src
    assert isinstance(inspect.getattr_static(WizardScreen, "_ensure_profile_row"), staticmethod)


def test_tactical_cm_wiring_is_split():
    from Programma_CS2_RENAN.apps.qt_app.screens.tactical_viewer_screen import TacticalViewerScreen

    gui_src = _method_source(TacticalViewerScreen, "_start_chronovisor_scan")
    assert "get_db_manager" not in gui_src
    assert "Worker(" in gui_src
    assert isinstance(
        inspect.getattr_static(TacticalViewerScreen, "_resolve_match_id_for_cm"),
        staticmethod,
    )


def test_no_screen_module_calls_db_outside_worker_functions():
    """Doctrine sweep: get_db_manager may appear in screens ONLY inside the
    three sanctioned worker staticmethods (marked by their names)."""
    allowed_funcs = {"_ensure_profile_row", "_resolve_match_id_for_cm"}
    offenders = []
    for py in sorted(_SCREENS.glob("*_screen.py")):
        tree = ast.parse(py.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                src_names = {n.id for n in ast.walk(node) if isinstance(n, ast.Name)} | {
                    n.attr for n in ast.walk(node) if isinstance(n, ast.Attribute)
                }
                if "get_db_manager" in src_names and node.name not in allowed_funcs:
                    offenders.append(f"{py.name}:{node.name}")
    assert offenders == [], f"GUI-thread DB access in screens: {offenders}"
