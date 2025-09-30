from langgraph.graph import MessagesState, StateGraph, START, END
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate,SystemMessagePromptTemplate,HumanMessagePromptTemplate,MessagesPlaceholder
from langgraph.checkpoint.memory import MemorySaver
from typing_extensions import Literal
from llm import DeepSeekR1,DeepSeekV3
from tools.financial_report import get_financial_report
from tools.stock_price import analyze_stocks
from tools.response import ResponseFormat
from prompt import plan_prompt
from langgraph.prebuilt import ToolNode

memory = MemorySaver()
# Nodes
tools = [get_financial_report,analyze_stocks]    
deepseek_v3 = DeepSeekV3()
deepseek_r1 = DeepSeekR1()
llm_with_tools = deepseek_v3.bind_tools(tools)

class AgentState(MessagesState):
    plan: str
    structured_response: ResponseFormat
    
def plan_node(state: AgentState):
    # 创建消息列表
    prompt = plan_prompt

    # 调用 LLM
    response = deepseek_r1.invoke([SystemMessage(content=prompt),state["messages"][0]])
    
    state["plan"] = response.content
    print(state["plan"])
    return state

def llm_call(state: AgentState):
    """LLM decides whether to call a tool or not"""
    messages = [
        SystemMessage(
            content=f"""
你是一个思路清晰，有条理的金融分析师，必须严格按照以下金融分析计划执行：
    
当前金融分析计划：
{state["plan"]}

如果你认为计划已经执行到最后一步了，请在内容的末尾加上\nFinal Answer字样

示例：
分析报告xxxxxxxx
Final Answer
            """
        )
    ] + state["messages"]

    # 调用 LLM
    response = llm_with_tools.invoke(messages)

    # 将响应添加到消息列表中
    state["messages"].append(response)

    return state

def respond(state: AgentState):
    response = state["messages"][-1].content
    if "Final Answer" in response:
        response = response.split("Final Answer")[0].strip()
    response_complete = {"message": response, "status": "completed"}
    responseformat = ResponseFormat(**response_complete)
    return {"structured_response": responseformat}

# Conditional edge function to route to the tool node or end based upon whether the LLM made a tool call
def should_continue(state) -> Literal["tool_node", "respond"]:
    """Decide if we should continue the loop or stop based upon whether the LLM made a tool call"""
    messages = state["messages"]
    print("\nmessages:", messages)
    last_message = messages[-1]
    # If the LLM makes a tool call, then perform an action
    if "Final Answer" in last_message.content:
        return "respond"
    # Otherwise, we stop (reply to the user)
    return "Action"

class DataAnalyzeAgent:
    def __init__(self):
        # Build workflow
        agent_builder = StateGraph(AgentState)

        # Add nodes
        agent_builder.add_node("plan_node", plan_node)
        agent_builder.add_node("llm_call", llm_call)
        agent_builder.add_node("tool_node", ToolNode(tools))
        agent_builder.add_node("respond", respond)

        # Add edges to connect nodes
        agent_builder.add_edge(START, "plan_node")
        agent_builder.add_edge("plan_node", "llm_call")
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
