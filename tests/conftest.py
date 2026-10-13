"""Load an add-on of addons/ the way Hermes does: a package named after its directory, so its relative
imports (``from . import x``) resolve. No add-on module is ever imported from the test directory."""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

ADDONS = Path(__file__).resolve().parents[1] / "addons"


def load_addon(directory: str) -> types.ModuleType:
    name = "addon_" + directory.replace("-", "_")
    if name in sys.modules:
        return sys.modules[name]
    root = ADDONS / directory
    spec = importlib.util.spec_from_file_location(name, root / "__init__.py", submodule_search_locations=[str(root)])
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    for child in root.glob("*.py"):
        if child.stem != "__init__":
            setattr(module, child.stem, sys.modules.get(f"{name}.{child.stem}") or importlib.import_module(f"{name}.{child.stem}"))
    return module
