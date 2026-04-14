from __future__ import annotations

from types import SimpleNamespace

import pytest


@pytest.fixture
def test_settings():
    return SimpleNamespace(
        poll_concurrency_limit=5,
        outlier_std_threshold=2.0,
        min_sources_required=2,
        source_weights={
            "ecb": 1.0,
            "frankfurter": 0.9,
            "openexchange": 0.85,
            "currencyapi": 0.85,
        },
    )
