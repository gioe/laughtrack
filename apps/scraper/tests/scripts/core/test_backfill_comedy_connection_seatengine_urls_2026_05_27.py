import importlib.machinery
import importlib.util
import sys
from pathlib import Path
from types import ModuleType

_SCRAPER_ROOT = Path(__file__).resolve().parents[3]
_SCRIPT_PATH = _SCRAPER_ROOT / "scripts" / "core" / "backfill_comedy_connection_seatengine_urls_2026_05_27.py"


def _load_module() -> ModuleType:
    loader = importlib.machinery.SourceFileLoader(
        "backfill_comedy_connection_seatengine_urls_2026_05_27",
        str(_SCRIPT_PATH),
    )
    spec = importlib.util.spec_from_loader(
        "backfill_comedy_connection_seatengine_urls_2026_05_27",
        loader,
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["backfill_comedy_connection_seatengine_urls_2026_05_27"] = module
    loader.exec_module(module)
    return module


def test_task_2487_targets_comedy_connection_seatengine_urls():
    mod = _load_module()

    assert mod._CLUB_ID == 217
    assert mod._CLUB_NAME == "Comedy Connection"
    assert mod._SEATENGINE_ID == "14"
    assert mod._PUBLIC_SHOW_BASE == "https://events.ricomedyconnection.com"
    assert mod._METADATA_KEY == "task_2487_public_show_base"
