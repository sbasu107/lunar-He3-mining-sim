"""Backward-compatibility facade for reporting."""

from __future__ import annotations

import logging

from mining.config import HOURS_TO_MINUTES
from mining.reporting import Reporter as MiningReporter

logger = logging.getLogger(__name__)


class Reporter(MiningReporter):
    """Backward-compatibility adapter for Reporter logging to simulation.reporting."""

    logger: logging.Logger = logger


__all__ = ["HOURS_TO_MINUTES", "Reporter"]
