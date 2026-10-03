"""Controlled execution boundary for registered analytical tools."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal, TypedDict

import pandas as pd

from .tools import TOOL_REGISTRY, ToolError


class ExecutionError(TypedDict):
    code: str
    message: str


class ExecutionResponse(TypedDict):
    status: Literal["success", "error"]
    tool: str
    parameters: dict[str, Any]
    result: dict[str, Any] | None
    error: ExecutionError | None


class Executor:
    """Validate requests and execute only explicitly registered analytical tools."""

    def execute(
        self,
        frame: pd.DataFrame,
        request: Mapping[str, Any],
    ) -> ExecutionResponse:
        """Execute a structured request without selecting or discovering tools."""
        if not isinstance(request, Mapping):
            return self._error_response(
                tool="",
                parameters={},
                code="INVALID_PARAMETERS",
                message="Request must be a mapping.",
            )

        raw_tool = request.get("tool")
        tool_name = raw_tool if isinstance(raw_tool, str) else ""
        raw_parameters = request.get("parameters", {})
        parameters = dict(raw_parameters) if isinstance(raw_parameters, Mapping) else {}

        if not tool_name:
            return self._error_response(
                tool=tool_name,
                parameters=parameters,
                code="INVALID_PARAMETERS",
                message="Request field 'tool' must be a non-empty string.",
            )
        if tool_name not in TOOL_REGISTRY:
            return self._error_response(
                tool=tool_name,
                parameters=parameters,
                code="UNKNOWN_TOOL",
                message=f"Tool '{tool_name}' is not registered.",
            )
        if not isinstance(raw_parameters, Mapping):
            return self._error_response(
                tool=tool_name,
                parameters={},
                code="INVALID_PARAMETERS",
                message="Request field 'parameters' must be a mapping.",
            )

        try:
            result = TOOL_REGISTRY[tool_name](frame, **parameters)
        except ToolError as error:
            return self._error_response(
                tool=tool_name,
                parameters=parameters,
                code=error.code,
                message=str(error),
            )
        except TypeError as error:
            return self._error_response(
                tool=tool_name,
                parameters=parameters,
                code="INVALID_PARAMETERS",
                message=f"Invalid parameters for tool '{tool_name}': {error}",
            )
        except Exception:
            return self._error_response(
                tool=tool_name,
                parameters=parameters,
                code="EXECUTION_ERROR",
                message=f"Tool '{tool_name}' could not be executed.",
            )

        return {
            "status": "success",
            "tool": tool_name,
            "parameters": parameters,
            "result": result,
            "error": None,
        }

    @staticmethod
    def _error_response(
        tool: str,
        parameters: dict[str, Any],
        code: str,
        message: str,
    ) -> ExecutionResponse:
        return {
            "status": "error",
            "tool": tool,
            "parameters": parameters,
            "result": None,
            "error": {"code": code, "message": message},
        }
