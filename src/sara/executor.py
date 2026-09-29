"""
Validated tool execution for SARA.

Tool calls must pass the policy layer before execution.
The model never executes tools directly.
"""

from .policy import validate_tool_call
from .tools import search_openalex


def execute_tool(tool_name: str, arguments: dict) -> dict:
    """
    Validate and execute an approved SARA tool call.

    Args:
        tool_name: Name of the requested tool.
        arguments: Arguments proposed for the tool.

    Returns:
        A structured execution result.
    """

    validation = validate_tool_call(tool_name, arguments)

    if not validation["allowed"]:
        return {
            "status": "REJECTED",
            "tool": tool_name,
            "reason": validation["reason"],
            "result": None,
        }

    if tool_name == "search_openalex":
        result = search_openalex(
            query=arguments["query"],
            max_results=arguments.get("max_results", 5),
        )

        return {
            "status": "COMPLETED",
            "tool": tool_name,
            "reason": "Validated tool call executed successfully.",
            "result": result,
        }

    return {
        "status": "FAILED_SAFELY",
        "tool": tool_name,
        "reason": "No executor is available for this tool.",
        "result": None,
    }