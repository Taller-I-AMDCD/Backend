"""Replaceable coordination decision contract."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Mapping, Protocol, runtime_checkable

from .context import ExecutionContext
from .contracts import ComponentId
from .exceptions import InvalidIdentifierError, OrchestrationError


class CoordinationAction(str, Enum):
    """Infrastructure-level actions available to a coordination strategy."""

    EXECUTE = "execute"
    COMPLETE = "complete"
    FAIL = "fail"


@dataclass(frozen=True, slots=True)
class CoordinationDecision:
    """Neutral decision returned by a replaceable coordination strategy."""

    action: CoordinationAction
    component_id: ComponentId | None = None
    payload: Mapping[str, object] = field(default_factory=dict)
    metadata: Mapping[str, object] = field(default_factory=dict)
    reason: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.action, CoordinationAction):
            raise OrchestrationError("action must be a CoordinationAction")
        if self.action is CoordinationAction.EXECUTE:
            if (
                not isinstance(self.component_id, str)
                or not self.component_id.strip()
            ):
                raise InvalidIdentifierError(
                    "component_id is required for an execute decision"
                )
        elif self.component_id is not None:
            raise OrchestrationError(
                "component_id is only valid for an execute decision"
            )
        object.__setattr__(self, "payload", dict(self.payload))
        object.__setattr__(self, "metadata", dict(self.metadata))


@runtime_checkable
class CoordinationStrategy(Protocol):
    """Select the next neutral action without executing components."""

    def decide(self, context: ExecutionContext) -> CoordinationDecision:
        """Return the next decision from the current execution context."""

        ...
