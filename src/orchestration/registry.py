"""In-memory registry for strategy-neutral orchestration components."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from .contracts import ComponentId, ComponentRequest, ComponentResult
from .exceptions import (
    ComponentNotFoundError,
    DuplicateComponentError,
    InvalidIdentifierError,
)


@runtime_checkable
class Component(Protocol):
    """Structural contract implemented by any registrable component."""

    @property
    def component_id(self) -> ComponentId:
        """Return the stable identifier used by the registry."""

        ...

    def handle(self, request: ComponentRequest) -> ComponentResult:
        """Handle a component request when invoked by future coordination code."""

        ...


class ComponentRegistry:
    """Store available components without selecting or executing them."""

    def __init__(self) -> None:
        self._components: dict[ComponentId, Component] = {}

    def register(self, component: Component) -> None:
        component_id = component.component_id
        self._validate_component_id(component_id)
        if component_id in self._components:
            raise DuplicateComponentError(
                f"component is already registered: {component_id}"
            )
        self._components[component_id] = component

    def contains(self, component_id: ComponentId) -> bool:
        self._validate_component_id(component_id)
        return component_id in self._components

    def get(self, component_id: ComponentId) -> Component:
        self._validate_component_id(component_id)
        try:
            return self._components[component_id]
        except KeyError as error:
            raise ComponentNotFoundError(
                f"component is not registered: {component_id}"
            ) from error

    def list_ids(self) -> tuple[ComponentId, ...]:
        """Return identifiers in deterministic registration order."""

        return tuple(self._components)

    def unregister(self, component_id: ComponentId) -> Component:
        """Remove and return a component using the same lookup guarantees."""

        component = self.get(component_id)
        del self._components[component_id]
        return component

    @staticmethod
    def _validate_component_id(component_id: ComponentId) -> None:
        if not isinstance(component_id, str) or not component_id.strip():
            raise InvalidIdentifierError(
                "component_id must be a non-empty string"
            )
