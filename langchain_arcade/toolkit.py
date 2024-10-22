from typing import Optional

from arcadepy import Arcade
from arcadepy.types.shared import ToolDefinition
from langchain_core.tools import StructuredTool

from langchain_arcade._utilities import (
    wrap_arcade_tool,
)


class ArcadeToolkit:
    """
    Arcade toolkit for LangChain framework.

    This class wraps Arcade tools as LangChain `StructuredTool` objects for integration.
    """

    def __init__(
        self,
        client: Optional[Arcade] = None,
        tools: Optional[list[str]] = None,
        toolkits: Optional[list[str]] = None,
    ):
        """Initialize the ArcadeToolkit.

        Args:
            tools: Optional list of tool names to include.
            toolkits: Optional list of toolkits to include.
            client: Optional Arcade client instance.
        """
        self.client = client or Arcade()
        self._tools = self._retrieve_tool_definitions(tools, toolkits)

    def _retrieve_tool_definitions(
        self, tools: Optional[list[str]] = None, toolkits: Optional[list[str]] = None
    ) -> list[ToolDefinition]:
        tool_definitions = []
        if tools or toolkits:
            if tools:
                tool_definitions.extend(
                    self.client.tools.definition.get(
                        director_id="default", tool_id=tool_id
                    )
                    for tool_id in tools
                )
            if toolkits:
                for tk in toolkits:
                    tool_definitions.extend(self.client.tools.list(toolkit=tk))
        else:
            # retrieve all tools
            tool_definitions = self.client.tools.list()
        return tool_definitions

    def get_tools(self, langgraph: bool = False) -> list[StructuredTool]:
        """Get Arcade tools wrapped as LangChain StructuredTool objects.

        Args:
            langgraph: Whether to use LangGraph-specific behavior.

        Returns:
            List of StructuredTool instances.
        """
        lc_tools = []
        for tool_def in self._tools:
            try:
                lc_tool = wrap_arcade_tool(self.client, tool_def, langgraph)
                lc_tools.append(lc_tool)
            # TODO: handle errors more specifically
            except Exception as e:
                # Log the error and continue with the next tool
                print(f"Failed to wrap tool '{tool_def.name}': {e}")
        return lc_tools
