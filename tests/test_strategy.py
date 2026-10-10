"""Tests for replaceable coordination decision contracts."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


SOURCE_ROOT = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SOURCE_ROOT))

from orchestration import (  # noqa: E402
    ComponentId,
    CoordinationAction,
    CoordinationDecision,
    CoordinationStrategy,
    ExecutionContext,
    InvalidIdentifierError,
)


class FakeStrategy:
    def decide(self, context: ExecutionContext) -> CoordinationDecision:
        return CoordinationDecision(action=CoordinationAction.COMPLETE)


class CoordinationDecisionTests(unittest.TestCase):
    def test_execute_requires_component_id(self) -> None:
        with self.assertRaises(InvalidIdentifierError):
            CoordinationDecision(action=CoordinationAction.EXECUTE)

    def test_complete_does_not_require_component(self) -> None:
        decision = CoordinationDecision(action=CoordinationAction.COMPLETE)

        self.assertIsNone(decision.component_id)

    def test_fail_preserves_reason(self) -> None:
        decision = CoordinationDecision(
            action=CoordinationAction.FAIL,
            reason="controlled stop",
        )

        self.assertEqual(decision.reason, "controlled stop")

    def test_decision_preserves_payload_and_metadata_defensively(self) -> None:
        payload = {"input": 1}
        metadata = {"source": "test"}
        decision = CoordinationDecision(
            action=CoordinationAction.EXECUTE,
            component_id=ComponentId("component-1"),
            payload=payload,
            metadata=metadata,
        )
        payload["input"] = 2
        metadata["source"] = "changed"

        self.assertEqual(decision.payload["input"], 1)
        self.assertEqual(decision.metadata["source"], "test")

    def test_strategy_uses_structural_protocol(self) -> None:
        self.assertIsInstance(FakeStrategy(), CoordinationStrategy)


if __name__ == "__main__":
    unittest.main()
