"""
Tool validation policy for SARA.

Model-proposed tool calls must be validated before execution.
The language model is not allowed to execute tools directly.
"""


ALLOWED_TOOLS = {
    "search_openalex",
}


def validate_tool_call(tool_name: str, arguments: dict) -> dict:
    """
    Validate a proposed tool call before execution.

    Args:
        tool_name: Name of the requested tool.
        arguments: Arguments proposed for the tool.

    Returns:
        A validation result describing whether execution is allowed.
    """

    if tool_name not in ALLOWED_TOOLS:
        return {
            "allowed": False,
            "reason": f"Tool '{tool_name}' is not allowed.",
        }

    if not isinstance(arguments, dict):
        return {
            "allowed": False,
            "reason": "Tool arguments must be a dictionary.",
        }

    if tool_name == "search_openalex":
        query = arguments.get("query", "")
        max_results = arguments.get("max_results", 5)

        if not isinstance(query, str) or not query.strip():
            return {
                "allowed": False,
                "reason": "OpenAlex search query must not be empty.",
            }

        if not isinstance(max_results, int) or not 1 <= max_results <= 20:
            return {
                "allowed": False,
                "reason": "max_results must be an integer between 1 and 20.",
            }

    return {
        "allowed": True,
        "reason": "Tool call passed validation.",
    }