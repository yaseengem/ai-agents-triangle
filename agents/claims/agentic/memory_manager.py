"""
Memory manager for the Claims Processing agent.

Wraps LocalMemoryStore to provide a typed, rule-oriented interface.
A module-level singleton is created on import so all code in the process
shares the same in-memory state (rules cache) on top of the persisted JSON.
"""

from __future__ import annotations

import os
import sys

# Add repo root to path so storage.memory_backend is importable when this
# module is loaded from agents/claims/agentic/ via uvicorn.
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from utils.logger import get_logger  # noqa: E402

logger = get_logger(__name__)

from storage.memory_backend import create_memory_backend  # noqa: E402
from .prompts import DEFAULT_RULES  # noqa: E402

_RULES_KEY = "agent_rules"


class ClaimsMemoryManager:
    """Typed wrapper around the memory backend for claims rules."""

    def __init__(self) -> None:
        self._store = create_memory_backend("claims")
        self._seed_defaults()

    # ── seeding ──────────────────────────────────────────────────────────────

    def _seed_defaults(self) -> None:
        """Persist DEFAULT_RULES on first run if no rules are stored yet."""
        if self._store.get(_RULES_KEY) is None:
            self._store.set(_RULES_KEY, DEFAULT_RULES)

    # ── rule access ──────────────────────────────────────────────────────────

    def get_rules(self) -> list[str]:
        rules = self._store.get(_RULES_KEY) or list(DEFAULT_RULES)
        logger.debug("[MEMORY] get_rules  count=%d", len(rules))
        return rules

    def set_rules(self, rules: list[str]) -> None:
        logger.info("[MEMORY] set_rules  count=%d", len(rules))
        self._store.set(_RULES_KEY, rules)

    def add_rule(self, rule: str) -> None:
        rules = self.get_rules()
        if rule not in rules:
            rules.append(rule)
            self.set_rules(rules)
            logger.info("[MEMORY] add_rule  rule=%s  new_total=%d", rule, len(rules))

    def remove_rule(self, rule: str) -> None:
        rules = self.get_rules()
        new_rules = [r for r in rules if r != rule]
        self.set_rules(new_rules)
        logger.info("[MEMORY] remove_rule  rule=%s  new_total=%d", rule, len(new_rules))


# Module-level singleton — one instance per process.
memory_manager = ClaimsMemoryManager()
