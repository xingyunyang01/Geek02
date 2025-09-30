import logging

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import (
    InternalError,
    InvalidParamsError,
    Part,
    Task,
    TaskState,
    TextPart,
    UnsupportedOperationError,
)
from a2a.utils import (
    new_agent_text_message,
    new_task,
)
from a2a.utils.errors import ServerError

from agent import DataAnalyzeAgent


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataAnalyzeAgentExecutor(AgentExecutor):
    """数据分析助手AgentExecutor"""

    def __init__(self):
        self.agent = DataAnalyzeAgent()

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        error = self._validate_request(context)
        if error:
            raise ServerError(error=InvalidParamsError())

        query = context.get_user_input()
        task = context.current_task
        if not task:
            task = new_task(context.message)
            event_queue.enqueue_event(task)
        updater = TaskUpdater(event_queue, task.id, task.contextId)
        try:
            response = await self.agent.invoke(query, task.contextId)
            is_task_complete = response['is_task_complete']
            require_user_input = response['require_user_input']
            print(response)
            if not is_task_complete and not require_user_input:
                updater.update_status(
                    TaskState.working,
                    new_agent_text_message(
                        response['content'],
                        task.contextId,
                        task.id,
                    ),
                )
            elif require_user_input:
                updater.update_status(
                    TaskState.input_required,
                    new_agent_text_message(
                        response['content'],
                        task.contextId,
                        task.id,
                    ),
                    final=True,
                )
            else:
                updater.add_artifact(
                    [Part(root=TextPart(text=response['content']))],
                    name='conversion_result',
                )
                updater.complete()

        except Exception as e:
            logger.error(f'An error occurred while streaming the response: {e}')
            raise ServerError(error=InternalError()) from e

    def _validate_request(self, context: RequestContext) -> bool:
        return False

    async def cancel(
        self, request: RequestContext, event_queue: EventQueue
    ) -> Task | None:
        raise ServerError(error=UnsupportedOperationError())
