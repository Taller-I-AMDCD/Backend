"""Unit tests for the strategy-neutral component registry."""

from __future__ import annotations

import sys
import unittest
from dataclasses import dataclass
from pathlib import Path


SOURCE_ROOT = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SOURCE_ROOT))

from orchestration import (  # noqa: E402
    Component,
    ComponentId,
    ComponentNotFoundError,
    ComponentRegistry,
    ComponentRequest,
    ComponentResult,
    ComponentStatus,
    DuplicateComponentError,
    InvalidIdentifierError,
    OrchestrationError,
)


@dataclass
class FakeComponent:
    component_id: ComponentId
    call_count: int = 0

    def handle(self, request: ComponentRequest) -> ComponentResult:
        self.call_count += 1
        return ComponentResult(
            component_id=self.component_id,
            status=ComponentStatus.SUCCESS,
            output=request.payload,
        )


class ComponentRegistryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = ComponentRegistry()
        self.component = FakeComponent(ComponentId("component-1"))

    def test_component_protocol_supports_structural_implementations(self) -> None:
        self.assertIsInstance(self.component, Component)

    def test_register_and_contains_component(self) -> None:
        self.registry.register(self.component)

        self.assertTrue(self.registry.contains(self.component.component_id))

    def test_get_returns_registered_component(self) -> None:
        self.registry.register(self.component)

        self.assertIs(self.registry.get(self.component.component_id), self.component)

    def test_list_ids_preserves_registration_order(self) -> None:
        second = FakeComponent(ComponentId("component-2"))
        self.registry.register(self.component)
        self.registry.register(second)

        self.assertEqual(
            self.registry.list_ids(),
            (ComponentId("component-1"), ComponentId("component-2")),
        )

    def test_duplicate_registration_raises_domain_error(self) -> None:
        self.registry.register(self.component)

        with self.assertRaises(DuplicateComponentError):
            self.registry.register(FakeComponent(ComponentId("component-1")))

    def test_unknown_component_raises_domain_error(self) -> None:
        with self.assertRaises(ComponentNotFoundError):
            self.registry.get(ComponentId("missing"))

    def test_distinct_components_can_coexist(self) -> None:
        self.registry.register(self.component)
        self.registry.register(FakeComponent(ComponentId("component-2")))

        self.assertEqual(len(self.registry.list_ids()), 2)

    def test_registration_does_not_execute_component(self) -> None:
        self.registry.register(self.component)

        self.assertEqual(self.component.call_count, 0)

    def test_empty_component_id_is_rejected(self) -> None:
        with self.assertRaises(InvalidIdentifierError):
            self.registry.register(FakeComponent(ComponentId("")))

    def test_unregister_removes_and_returns_component(self) -> None:
        self.registry.register(self.component)

        removed = self.registry.unregister(self.component.component_id)

        self.assertIs(removed, self.component)
        self.assertFalse(self.registry.contains(self.component.component_id))

    def test_registry_errors_share_common_base(self) -> None:
        self.assertTrue(issubclass(DuplicateComponentError, OrchestrationError))
        self.assertTrue(issubclass(ComponentNotFoundError, OrchestrationError))


if __name__ == "__main__":
    unittest.main()
