import logging
import click
import httpx
import sys
import uvicorn

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryPushNotifier, InMemoryTaskStore
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
)

from agent import DataAnalyzeAgent
from agent_executor import DataAnalyzeAgentExecutor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@click.command()
@click.option('--host', 'host', default='localhost')
@click.option('--port', 'port', default=10001)
def main(host, port):
    try:
        capabilities = AgentCapabilities(streaming=False, pushNotifications=True)
        skill = AgentSkill(
            id='数据分析',
            name='数据分析工具',
            description='可以分析股票股价表现，财务情况等',
            tags=['数据分析'],
            examples=['对比一下 600600, 002461, 000729, 600573的股价表现和财务情况，哪家更值得投资'],
        )
        agent_card = AgentCard(
            name='data_analyze_Agent',
            description='可以分析股票股价表现，财务情况等',
            url=f'http://{host}:{port}/',
            version='1.0.0',
            defaultInputModes=DataAnalyzeAgent.SUPPORTED_CONTENT_TYPES,
            defaultOutputModes=DataAnalyzeAgent.SUPPORTED_CONTENT_TYPES,
            capabilities=capabilities,
            skills=[skill],
        )

        # --8<-- [start:DefaultRequestHandler]
        httpx_client = httpx.AsyncClient()
        request_handler = DefaultRequestHandler(
            agent_executor=DataAnalyzeAgentExecutor(),
            task_store=InMemoryTaskStore(),
            push_notifier=InMemoryPushNotifier(httpx_client),
        )
        server = A2AStarletteApplication(
            agent_card=agent_card, http_handler=request_handler
        )

        uvicorn.run(server.build(), host=host, port=port)

    except Exception as e:
        logger.error(f'An error occurred during server startup: {e}')
        sys.exit(1)

if __name__ == '__main__':
    main()