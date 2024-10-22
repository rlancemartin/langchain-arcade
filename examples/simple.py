import os

from langchain import hub
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain_openai import ChatOpenAI

from langchain_arcade import ArcadeToolkit

# Pull relevant agent model.
prompt = hub.pull("hwchase17/openai-functions-agent")

# Get all the tools available in Arcade
arcade_toolkit = ArcadeToolkit()
tools = arcade_toolkit.get_tools()

openai_client = ChatOpenAI(api_key=os.environ["OPENAI_API_KEY"])

# Define agent
agent = create_openai_functions_agent(openai_client, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

# Execute using agent_executor
agent_executor.invoke({"input": "Lookup Sam Partee on Google"})
