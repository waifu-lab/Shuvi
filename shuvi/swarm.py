from typing import Dict, List, Optional

from shuvi.agent import Agent
from shuvi.types import AgentResult, AppMessage


class Swarm:
    """
    Routes messages across multiple named agents using the handoff mechanism.

    An agent signals a handoff by raising HandoffSignal(target) inside a tool call.
    Swarm catches the result.handoff field and re-runs with the target agent,
    passing the current message history forward.
    """

    def __init__(self, agents: Dict[str, Agent], max_handoffs: int = 10) -> None:
        self._agents = agents
        self._max_handoffs = max_handoffs

    def add_agent(self, name: str, agent: Agent) -> None:
        self._agents[name] = agent

    async def run(
        self,
        entry: str,
        messages: Optional[List[AppMessage]] = None,
    ) -> AgentResult:
        current_name = entry
        current_messages = messages
        last_result: Optional[AgentResult] = None
        handoffs = 0

        while True:
            agent = self._agents.get(current_name)
            if agent is None:
                raise KeyError(f"Agent '{current_name}' not found in swarm")

            if agent._context_manager is not None:
                result = await agent.run()
            else:
                result = await agent.run(current_messages)

            last_result = result

            if result.handoff is None:
                break

            if handoffs >= self._max_handoffs:
                break

            handoffs += 1
            current_name = result.handoff
            current_messages = result.messages

        return last_result
