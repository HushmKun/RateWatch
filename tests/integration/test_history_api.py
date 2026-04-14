from __future__ import annotations

import pytest


pytestmark = pytest.mark.skip(reason="Requires Redis/Postgres integration stack.")


def test_history_api_placeholder():
    assert True
