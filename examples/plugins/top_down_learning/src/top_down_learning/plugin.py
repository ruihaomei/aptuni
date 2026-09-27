"""Entry point declared by ``aptuni-plugin.toml``."""

from __future__ import annotations

from aptuni.api.v1 import AptuniAPI
from top_down_learning.workflow import TopDownLearning


def create_plugin(api: AptuniAPI) -> TopDownLearning:
    return TopDownLearning(api)
