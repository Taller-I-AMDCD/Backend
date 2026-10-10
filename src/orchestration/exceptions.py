"""Domain errors raised by neutral orchestration infrastructure."""


class OrchestrationError(Exception):
    """Base error for expected orchestration infrastructure failures."""


class DuplicateComponentError(OrchestrationError):
    """Raised when a component identifier is already registered."""


class ComponentNotFoundError(OrchestrationError):
    """Raised when a requested component is not registered."""


class InvalidStateTransitionError(OrchestrationError, ValueError):
    """Raised when an execution lifecycle transition is not allowed."""


class InvalidIdentifierError(OrchestrationError, ValueError):
    """Raised when an orchestration identifier is empty or malformed."""


class MaxStepsExceededError(OrchestrationError):
    """Raised when a defective strategy exceeds the defensive step limit."""
