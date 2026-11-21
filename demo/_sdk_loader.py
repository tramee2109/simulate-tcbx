"""Helper to load `the20-simulate-sdk` from the parent directory without pip install."""

import importlib.util
import os
import sys


def load_sdk():
    sdk_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    spec = importlib.util.spec_from_file_location(
        "the20_simulate_sdk",
        os.path.join(sdk_dir, "__init__.py"),
        submodule_search_locations=[sdk_dir],
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["the20_simulate_sdk"] = mod
    spec.loader.exec_module(mod)
    return mod
