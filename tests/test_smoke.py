"""Smoke test: the package imports and exposes its version.

This guards the scaffolding commit — later commits replace this with real
coverage ported from the bats suite.
"""

from __future__ import annotations

import addsong


def test_version_is_a_string() -> None:
    assert isinstance(addsong.__version__, str)
    assert addsong.__version__ == "1.0.0"
