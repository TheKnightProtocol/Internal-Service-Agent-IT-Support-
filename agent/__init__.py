"""Internal IT Service Agent package (auto-detecting)."""
import importlib
import pkgutil
from pathlib import Path

# Try common module names in priority order.
_CANDIDATE_MODULES = ("service", "agent", "core", "main", "engine", "app")

ITServiceAgent = None
for _name in _CANDIDATE_MODULES:
    try:
        _mod = importlib.import_module(f".{_name}", package=__name__)
        if hasattr(_mod, "ITServiceAgent"):
            ITServiceAgent = _mod.ITServiceAgent
            break
    except ModuleNotFoundError:
        continue

# Fallback: scan all .py files in this package.
if ITServiceAgent is None:
    _pkg_dir = Path(__file__).resolve().parent
    for _finder, _name, _ispkg in pkgutil.iter_modules([str(_pkg_dir)]):
        if _name.startswith("_"):
            continue
        try:
            _mod = importlib.import_module(f".{_name}", package=__name__)
            if hasattr(_mod, "ITServiceAgent"):
                ITServiceAgent = _mod.ITServiceAgent
                break
        except Exception:
            continue

if ITServiceAgent is None:
    raise ImportError(
        "Could not find class ITServiceAgent in the agent/ package. "
        "Checked modules: " + ", ".join(_CANDIDATE_MODULES)
    )

__all__ = ["ITServiceAgent"]
