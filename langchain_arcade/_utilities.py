import json
from typing import Any, Callable, Union

from arcadepy import Arcade
from arcadepy.types.shared import ToolDefinition
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field, ValidationError, create_model
from pydantic.v1 import ValidationError as PydanticV1ValidationError

# Check if LangGraph is enabled
LANGGRAPH_ENABLED = True
try:
    from langgraph.errors import NodeInterrupt
except ImportError:
    LANGGRAPH_ENABLED = False

# Mapping of Arcade value types to Python types
TYPE_MAPPING = {
    "string": str,
    "number": float,
    "integer": int,
    "boolean": bool,
    "array": list,
    "object": dict,
}

def get_python_type(val_type: str) -> Any:
    """Map Arcade value types to Python types.

    Args:
        val_type: The value type as a string.

    Returns:
        Corresponding Python type.
    """
    return TYPE_MAPPING.get(val_type, Any)

def tool_definition_to_pydantic_model(tool_def: ToolDefinition) -> type[BaseModel]:
    """Convert a ToolDefinition's inputs into a Pydantic BaseModel.

    Args:
        tool_def: The ToolDefinition object to convert.

    Returns:
        A Pydantic BaseModel class representing the tool's input schema.
    """
    fields: dict[str, Any] = {}
    for param in tool_def.inputs.parameters:
        param_type = get_python_type(param.value_schema.val_type)
        param_description = param.description or "No description provided."
        default = ... if param.required else None
        fields[param.name] = (
            param_type,
            Field(default=default, description=param_description),
        )
    return create_model(f"{tool_def.name}Args", **fields)

def create_tool_function(  # type: ignore[C901]  # noqa: C901
    client: Arcade,
    tool_def: ToolDefinition,
    args_schema: type[BaseModel],
    langgraph: bool = False,
) -> Callable:
    """Create a callable function to execute an Arcade tool.

    Args:
        client: The Arcade client instance.
        tool_def: The ToolDefinition of the tool to wrap.
        args_schema: The Pydantic model representing the tool's arguments.
        langgraph: Whether to enable LangGraph-specific behavior.

    Returns:
        A callable function that executes the tool.
    """
    if langgraph and not LANGGRAPH_ENABLED:
        raise ImportError(
            "LangGraph is not installed. Please install it to use this feature."
        )

    toolkit_name = tool_def.toolkit.name
    full_tool_name = f"{toolkit_name}.{tool_def.name}"
    requires_authorization = tool_def.requirements.authorization is not None

    def tool_function(config: RunnableConfig, **kwargs: Any) -> Any:
        """Execute the Arcade tool with the given parameters.

        Args:
            config: RunnableConfig containing execution context.
            **kwargs: Tool input arguments.

        Returns:
            The output from the tool execution.
        """
        user_id = config.get("configurable", {}).get("user_id") if config else None

        if requires_authorization:
            if not user_id:
                error_message = f"user_id is required to run {full_tool_name}"
                if langgraph:
                    raise NodeInterrupt(error_message)
                return {"error": error_message}

            # Authorize the user for the tool
            auth_response = client.tools.authorize(
                tool_name=full_tool_name, user_id=user_id
            )
            if auth_response.status != "completed":
                auth_message = (
                    "Please use the following link to authorize: "
                    f"{auth_response.authorization_url}"
                )
                if langgraph:
                    raise NodeInterrupt(auth_message)
                return {"error": auth_message}

        # Validate input arguments using the args_schema
        try:
            args_schema(**kwargs)
        except (ValidationError, PydanticV1ValidationError) as e:
            error_message = parse_pydantic_error(e)
            if langgraph:
                raise NodeInterrupt(error_message)
            return {"error": error_message}

        # Execute the tool with provided inputs
        inputs_json = json.dumps(kwargs)
        execute_response = client.tools.execute(
            tool_name=full_tool_name, inputs=inputs_json, user_id=user_id
        )

        if execute_response.success:
            return execute_response.output.value
        error_message = execute_response.output.error
        if langgraph:
            raise NodeInterrupt(error_message)
        return {"error": error_message}

    return tool_function

def parse_pydantic_error(
    e: Union[ValidationError, PydanticV1ValidationError]
) -> str:
    """Parse Pydantic validation error.

    Args:
        e: The ValidationError exception.

    Returns:
        A formatted error message.
    """
    message = "Invalid request data provided"
    missing = []
    others = []
    for error in e.errors():
        param = ".".join(map(str, error["loc"]))
        if error["type"] == "missing":
            missing.append(param)
            continue
        others.append(f"{error['msg']} on parameter `{param}`")
    if missing:
        message += f"\n- Missing fields: {', '.join(set(missing))}"
    if others:
        message += "\n- " + "\n- ".join(others)
    return message

def wrap_arcade_tool(
    client: Arcade,
    tool_def: ToolDefinition,
    langgraph: bool = False,
) -> StructuredTool:
    """Wrap an Arcade `ToolDefinition` as a LangChain `StructuredTool`.

    Args:
        client: The Arcade client instance.
        tool_def: The ToolDefinition object to wrap.
        langgraph: Whether to enable LangGraph-specific behavior.

    Returns:
        A StructuredTool instance representing the Arcade tool.
    """
    tool_name = tool_def.name
    description = tool_def.description or "No description provided."

    # Create a Pydantic model for the tool's input arguments
    args_schema = tool_definition_to_pydantic_model(tool_def)

    # Create the action function
    action_func = create_tool_function(
        client=client,
        tool_def=tool_def,
        args_schema=args_schema,
        langgraph=langgraph,
    )

    # Create the StructuredTool instance
    return StructuredTool.from_function(
        func=action_func,
        name=tool_name,
        description=description,
        args_schema=args_schema,
        inject_kwargs={"user_id"},
    )
