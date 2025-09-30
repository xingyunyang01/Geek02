from collections.abc import AsyncIterable
from typing import Any
from langgraph.graph import MessagesState, StateGraph, START, END
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
from langgraph.checkpoint.memory import MemorySaver
from typing_extensions import Literal
from tools import tools, llm_with_tools,ResponseFormat
from langgraph.prebuilt import ToolNode

memory = MemorySaver()

class AgentState(MessagesState):
    # Final structured response from the agent
    structured_response: ResponseFormat

# Nodes
def llm_call(state: AgentState):
    """LLM decides whether to call a tool or not"""
    # 创建消息列表
    messages = [
        SystemMessage(
            content="""
            你是一个股票信息问答助手
            你的唯一目的是使用'get_stock_info'工具去回答有关股票信息的问题
            如果用户询问与股票信息无关的问题, 
            礼貌地说明您无法帮助处理该主题
            不要试图回答无关的问题或将工具用于其他目的。
            如果用户需要提供更多信息，将响应状态设置为 input_required。
            如果在处理请求时出现错误，则将响应状态设置为 error。
            如果请求已完成，则将响应状态设置为 completed。
            """
        )
    ] + state["messages"]
    
    # 调用 LLM
    response = llm_with_tools.invoke(messages)
    
    return {
        "messages": [response]
    }

def respond(state: AgentState):
    # Construct the final answer from the arguments of the last tool call
    format_tool_call = state["messages"][-1].tool_calls[0]
    print("\nformat_tool_call:", format_tool_call)
    response = ResponseFormat(**format_tool_call["args"])
    print("response:", response)
    # Since we're using tool calling to return structured output,
    # we need to add  a tool message corresponding to the WeatherResponse tool call,
    # This is due to LLM providers' requirement that AI messages with tool calls
    # need to be followed by a tool message for each tool call
    tool_message = {
        "type": "tool",
        "content": "Here is your structured response",
        "tool_call_id": format_tool_call["id"],
    }
    # We return the final answer
    return {"structured_response": response, "messages": [tool_message]}

# Conditional edge function to route to the tool node or end based upon whether the LLM made a tool call
def should_continue(state: MessagesState) -> Literal["tool_node", "respond"]:
    """Decide if we should continue the loop or stop based upon whether the LLM made a tool call"""
    messages = state["messages"]
    last_message = messages[-1]
    if len(last_message.tool_calls) == 1:
        if last_message.tool_calls[0]["name"] == "ResponseFormat":
            return "respond"
        else:
            return "Action"

class StockAgent:
    def __init__(self):
        # Build workflow
        agent_builder = StateGraph(MessagesState)

        # Add nodes
        agent_builder.add_node("llm_call", llm_call)
        agent_builder.add_node("tool_node", ToolNode(tools))
        agent_builder.add_node("respond", respond)

        # Add edges to connect nodes
        agent_builder.add_edge(START, "llm_call")
        agent_builder.add_conditional_edges(
            "llm_call",
            should_continue,
            {
                # Name returned by should_continue : Name of next node to visit
                "Action": "tool_node",
                "respond": "respond",
            },
        )
        agent_builder.add_edge("tool_node", "llm_call")
        agent_builder.add_edge("respond", END)

        # Compile the agent
        self.graph = agent_builder.compile(checkpointer=memory)

    async def invoke(self, query, context_id):
        config = {'configurable': {'thread_id': context_id}}
        messages = [HumanMessage(content=query)]
        self.graph.invoke({"messages": messages},config)
        return self.get_agent_response(config)

    async def stream(self, query, context_id) -> AsyncIterable[dict[str, Any]]:
        inputs = {'messages': [('user', query)]}
        config = {'configurable': {'thread_id': context_id}}

        for item in self.graph.stream(inputs, config, stream_mode='values'):
            message = item['messages'][-1]
            if (
                isinstance(message, AIMessage)
                and message.tool_calls
                and len(message.tool_calls) > 0
            ):
                yield {
                    'is_task_complete': False,
                    'require_user_input': False,
                    'content': 'Looking up the exchange rates...',
                }
            elif isinstance(message, ToolMessage):
                yield {
                    'is_task_complete': False,
                    'require_user_input': False,
                    'content': 'Processing the exchange rates..',
                }

        yield self.get_agent_response(config)

    def get_agent_response(self, config):
        current_state = self.graph.get_state(config)
        print(current_state)
        structured_response = current_state.values.get('structured_response')
        if structured_response and isinstance(
            structured_response, ResponseFormat
        ):
            if structured_response.status == 'input_required':
                return {
                    'is_task_complete': False,
                    'require_user_input': True,
                    'content': structured_response.message,
                }
            if structured_response.status == 'error':
                return {
                    'is_task_complete': False,
                    'require_user_input': True,
                    'content': structured_response.message,
                }
            if structured_response.status == 'completed':
                return {
                    'is_task_complete': True,
                    'require_user_input': False,
                    'content': structured_response.message,
                }

        return {
            'is_task_complete': False,
            'require_user_input': True,
            'content': (
                'We are unable to process your request at the moment. '
                'Please try again.'
            ),
        }

    SUPPORTED_CONTENT_TYPES = ['text', 'text/plain']