import importlib.util
import os
from pathlib import Path
import traceback


def _maybe_start_author_view():
    if os.environ.get("BUTTERFLY_AUTO_AUTHOR_VIEW") != "1":
        return
    scene_id = os.environ.get("BUTTERFLY_SCENE_ID", "F09")
    root = Path(__file__).resolve().parents[4]
    script_path = root / "Tools" / "unreal" / "open-author-view.py"
    try:
        spec = importlib.util.spec_from_file_location("butterfly_open_author_view", str(script_path))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.start_interactive_session(scene_id)
    except Exception:
        err_dir = root / "Evidence" / "Unreal" / scene_id
        err_dir.mkdir(parents=True, exist_ok=True)
        (err_dir / "author-view-error.txt").write_text(traceback.format_exc(), encoding="utf-8")


_maybe_start_author_view()
