
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

from langchain_arcade import ArcadeToolkit

tools = ArcadeToolkit().get_tools(langgraph=True)

model = ChatOpenAI(model="gpt-4o")

graph = create_react_agent(model, tools=tools)


inputs = {
    "messages": [
        ("user", "Star arcadeai/arcade-ai on Github!")
    ],

}
for chunk in graph.stream(inputs, stream_mode="values", config={
        "thread_id": "2",
        "user_id": "sam@arcade-ai.com"
    }
):
    print(chunk)
