import asyncio
from contextlib import AsyncExitStack
from openai import AsyncOpenAI
from typing import Any
import uuid
import json
import os
import re
from a2a.client import A2ACardResolver
from a2a.types import (
    AgentCard,
    DataPart,
    Message,
    MessageSendConfiguration,
    MessageSendParams,
    Part,
    Task,
    TaskState,
    TextPart,
)
from remote_agent_connection import RemoteAgentConnections, TaskUpdateCallback
import httpx
from typing import List

class HostAgent:
    def __init__(
        self,
        remote_agent_addresses: list[str],
        http_client: httpx.AsyncClient,
        task_callback: TaskUpdateCallback | None = None,
    ):
        self.task_callback = task_callback
        self.httpx_client = http_client
        self.remote_agent_connections: dict[str, RemoteAgentConnections] = {}
        self.cards: dict[str, AgentCard] = {}
        self.agents = ''
        self.remote_agent_addresses = remote_agent_addresses
        self.client = AsyncOpenAI(
            api_key=os.getenv("AliDeep"),  
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
        )

    async def connect_to_server(self):
        """Initialize the agent by fetching cards from remote agents"""
        for address in self.remote_agent_addresses:
            card_resolver = A2ACardResolver(httpx_client=self.httpx_client, base_url=address)
            card = await card_resolver.get_agent_card()
            remote_connection = RemoteAgentConnections(self.httpx_client, card)
            self.remote_agent_connections[card.name] = remote_connection
            self.cards[card.name] = card
        #列出可用的Agent
        agent_info = []
        for ra in self.list_remote_agents():
            agent_info.append(json.dumps(ra))
        self.agents = '\n'.join(agent_info)

    def list_remote_agents(self) -> List[dict]:
        """列出所有可用的远程Agent
        Returns:
            List[dict]: 一个包含Agent信息的字典列表
        """
        if not self.remote_agent_connections:
            return []

        remote_agent_info = []
        for card in self.cards.values():
            remote_agent_info.append(
                {'name': card.name, 'description': card.description}
            )
        return remote_agent_info
    
    async def send_message(self, agent_name: str, message: str) -> List[dict]:
        """向指定的远程Agent发送消息
        Args:
            agent_name: 远程Agent的名称
            message: 要发送的消息内容
        """
        if agent_name not in self.remote_agent_connections:
            raise ValueError(f'Agent {agent_name} not found')
        
        client = self.remote_agent_connections[agent_name]
        if not client:
            raise ValueError(f'Client not available for {agent_name}')
        
        messageId = str(uuid.uuid4())
        request: MessageSendParams = MessageSendParams(
            id=str(uuid.uuid4()),
            message=Message(
                role='user',
                parts=[TextPart(text=message)],
                messageId=messageId
            ),
            configuration=MessageSendConfiguration(
                acceptedOutputModes=['text', 'text/plain', 'image/png'],
            ),
        )
        response = await client.send_message(request, self.task_callback)
        # Extract text directly from response object
        if isinstance(response, Message):
            return [{"type": "message", "content": response.parts[0].text}]
        elif isinstance(response, Task):
            if response.artifacts and len(response.artifacts) > 0:
                for artifact in response.artifacts:
                    if artifact.parts and len(artifact.parts) > 0:
                        return [{"type": "task", "content": artifact.parts[0].root.text}]
            return [{"type": "task", "content": ""}]
        
        return []
    
    async def _send_messages(self, messages: list):
        return await self.client.chat.completions.create(
            model="qwen-max",
            messages=messages,
        )

    async def process_query(self, query: str) -> str:
        """Process a query using OpenAI and available tools"""
        agent_info = []
        for ra in self.list_remote_agents():
            agent_info.append(ra)
        #print("\navailable agents:", agent_info)

        messages = [
            {
                "role": "user",
                "content": """
You run in a loop of Thought, Action, Action Input, PAUSE, Observation.
At the end of the loop you output an Answer
Use Thought to describe your thoughts about the question you have been asked.
Use Action to run one of the actions available to you
use Action Input to indicate the input to the Action, which is a disassembly of the content for the user's question - then return PAUSE.
Observation will be the result of running those actions.

Your available actions are:
   
{agent_info}

Rules:
1- If the input is a greeting or a goodbye, respond directly in a friendly manner without using the Thought-Action loop.
2- Otherwise, follow the Thought-Action Input loop to find the best answer.
3- If you already have the answer to a part or the entire question, use your knowledge without relying on external actions.
4- If you need to execute more than one Action, do it on separate calls.
5- At the end, provide a final answer.

Some examples:

### 1
Question: 贵州茅台的收盘价是多少？
Thought: 我需要调用staock_Agent获取贵州茅台的收盘价
Action: staock_Agent
Action Input: 贵州茅台的收盘价是多少？

PAUSE

You will be called again with this:

Observation: 1700.

You then output: 
Final Answer: 贵州茅台的收盘价是1700.

Begin!

New input: {query}
""".format(agent_info=agent_info, query=query)
            }
        ]

        while True:
            # Initial OpenAI API call
            response = await self._send_messages(messages)
            message = response.choices[0].message
            print("\nmessage:", message.content)
            final_text = []
            final_text.append(message.content or "")

            final_answer_match = re.search(r'Final Answer:\s*(.*)', message.content)
            if final_answer_match:
                final_answer = final_answer_match.group(1)
                break
            
            messages.append({
                "role": "assistant",
                "content": message.content
            })

            action_match = re.search(r'Action:\s*(\w+)', message.content)
            action_input_match = re.search(r'Action Input:\s*(.*?)(?=\n|$)', message.content)
            
            if not action_match:
                raise ValueError(f"Could not find Action in response: {message.content}")
            if not action_input_match:
                raise ValueError(f"Could not find Action Input in response: {message.content}")
                
            agent = action_match.group(1)
            content = action_input_match.group(1).strip()

            print(f"\n需使用智能体{agent}")
            result = await self.send_message(agent, content)
            final_text.append(f"[Calling Agent {agent} with query {content}]")
            
            messages.append({
                "role": "user",
                "content": result[0].get('content', '')
            })

            # Get next response from OpenAI
            response = await self._send_messages(messages)
            
            message = response.choices[0].message
            if message.content:
                final_text.append(message.content)

        return "\n".join(final_text)

    async def chat_loop(self):
        """Run an interactive chat loop"""
        print("\nA2A Client Started!")
        print("Type your queries or 'quit' to exit.")
        
        while True:
            try:
                query = input("\nQuery: ").strip()
                if query.lower() == 'quit':
                    break
                response = await self.process_query(query)
                print("\n" + response)
            except Exception as e:
                print(f"\nError: {str(e)}")
    
    async def cleanup(self):
        """Clean up resources"""
        await self.exit_stack.aclose()

async def main():
    remote_agent_addresses = [
        "http://localhost:10000",
        "http://localhost:10001",
    ]
    # 创建异步HTTP客户端
    async with httpx.AsyncClient(timeout=50000) as client:
        # 初始化host agent
        host = HostAgent(
            remote_agent_addresses=remote_agent_addresses,
            http_client=client
        )
        await host.connect_to_server()

        try:
            await host.chat_loop()
        finally:
            await host.cleanup()

if __name__ == "__main__":
    asyncio.run(main())