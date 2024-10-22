from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode

from langchain_arcade import ArcadeToolkit


def check_authorize_status(user_id):
    return user_id == "sam@arcade-ai.com"

# Initialize the Arcade Toolkit with tools
tools = ArcadeToolkit().get_tools(langgraph=True)
tool_node = ToolNode(tools)

# Define the model
model = ChatOpenAI(model="gpt-4o")
model_with_tools = model.bind_tools(tools)

# Define the agent node
def call_agent(state):
    messages = state["messages"]
    response = model_with_tools.invoke(messages)
    return {"messages": [response]}

def should_continue(state: MessagesState):
    messages = state["messages"]
    last_message = messages[-1]
    if last_message.tool_calls:
        return "tools"
    return END


# Build the graph
workflow = StateGraph(MessagesState)

# Add nodes to the graph
workflow.add_node("agent", call_agent)
workflow.add_node("tools", tool_node)

# Define the edges and control flow
workflow.add_edge(START, "agent")
workflow.add_conditional_edges("agent", should_continue, ["tools", END])
workflow.add_edge("tools", "agent")

# Set up memory for checkpointing
memory = MemorySaver()

# Compile the graph with a breakpoint before 'check_authorization'
graph = workflow.compile(
    checkpointer=memory
)

# Input messages
inputs = {
    "messages": [
        HumanMessage(content="Star arcadeai/arcade-ai on GitHub!")
    ],
}

# Configuration with thread and user IDs
config = {
    "configurable": {
        "thread_id": "4",
        "user_id": "sam@partee.io"
    }
}

# Run the graph
for chunk in graph.stream(inputs, config=config, stream_mode="values"):
    chunk["messages"][-1].pretty_print()
