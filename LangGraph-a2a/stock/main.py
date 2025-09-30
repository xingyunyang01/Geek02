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

from agent import StockAgent
from agent_executor import StockAgentExecutor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@click.command()
@click.option('--host', 'host', default='localhost')
@click.option('--port', 'port', default=10000)
def main(host, port):
    try:
        capabilities = AgentCapabilities(streaming=False, pushNotifications=True)
        skill = AgentSkill(
            id='股票信息',
            name='股票信息查询工具',
            description='可以查询股票的代码，名称，收盘价等信息',
            tags=['股票信息'],
            examples=['300750是哪只股票的代码？'],
        )
        agent_card = AgentCard(
            name='stock_Agent',
            description='可以查询股票的代码，名称，收盘价等信息',
            url=f'http://{host}:{port}/',
            version='1.0.0',
            defaultInputModes=StockAgent.SUPPORTED_CONTENT_TYPES,
            defaultOutputModes=StockAgent.SUPPORTED_CONTENT_TYPES,
            capabilities=capabilities,
            skills=[skill],
        )

        # --8<-- [start:DefaultRequestHandler]
        httpx_client = httpx.AsyncClient()
        request_handler = DefaultRequestHandler(
            agent_executor=StockAgentExecutor(),
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