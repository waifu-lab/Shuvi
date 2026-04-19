import asyncio
import inspect
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from hai.providers.providers import ProviderText
from hai.tool import Tool

from shuvi.types import (
    AGENT_OUTCOME,
    AgentCallbacks,
    AgentConfig,
    AgentResult,
    ExecutionTrace,
    LoopConfig,
    Message,
    TokenUsage,
    ToolCallTrace,
    VerificationRecord,
    VerifyFn,
)


async def _emit(fn: Optional[Any], *args: Any) -> None:
    if fn is None:
        return
    if inspect.iscoroutinefunction(fn):
        await fn(*args)
    else:
        fn(*args)


class Agent:
    def __init__(self, config: AgentConfig):
        self._provider: ProviderText = config.provider
        self._system_prompt: str = config.system_prompt
        self._loop: LoopConfig = config.loop
        self._callbacks: AgentCallbacks = config.callbacks
        self._session_id: Optional[str] = config.session_id
        self._tools: List[Tool] = list(config.tools)
        self._tool_map: Dict[str, Tool] = {t.name: t for t in self._tools}
        self._message_queue: asyncio.Queue[Message] = asyncio.Queue()

    async def run(self, messages: List[Message]) -> AgentResult:
        """Execute the agent: inner tool loop + optional outer verify loop."""
        start = datetime.now()
        trace = ExecutionTrace(
            start_time=start.isoformat(),
            session_id=self._session_id,
        )

        current_messages = list(messages)
        verify_fn = self._loop.verify_completion
        max_outer = self._loop.max_outer_retries

        try:
            while True:
                (
                    final_msgs,
                    iterations,
                    tool_traces,
                    usage,
                    hit_max,
                ) = await self._inner_loop(current_messages)

                trace.inner_iterations += iterations
                trace.tool_calls.extend(tool_traces)
                trace.token_usage.input += usage.input
                trace.token_usage.output += usage.output
                trace.token_usage.total += usage.total

                if hit_max:
                    trace.outcome = AGENT_OUTCOME.max_iterations
                    break

                if verify_fn is None:
                    trace.outcome = AGENT_OUTCOME.completed
                    break

                verification = await _call_verify(verify_fn, final_msgs)
                trace.verifications.append(verification)

                if verification.passed:
                    trace.outcome = AGENT_OUTCOME.completed
                    break

                if trace.outer_retries >= max_outer:
                    trace.outcome = AGENT_OUTCOME.verify_failed
                    break

                trace.outer_retries += 1
                current_messages = final_msgs + [
                    {
                        "role": "user",
                        "content": f"驗證未通過：{verification.reason}，請修正",
                    }
                ]

        except Exception as e:
            trace.outcome = AGENT_OUTCOME.error
            await _emit(self._callbacks.error, e)
            final_msgs = current_messages
            if self._callbacks.error is None:
                raise

        end = datetime.now()
        trace.end_time = end.isoformat()
        trace.duration_ms = (end - start).total_seconds() * 1000

        return AgentResult(messages=final_msgs, trace=trace, outcome=trace.outcome)

    def queue_message(self, message: Message) -> None:
        self._message_queue.put_nowait(message)

    def add_tool(self, tool: Tool) -> None:
        self._tools.append(tool)
        self._tool_map[tool.name] = tool

    def remove_tool(self, name: str) -> None:
        self._tools = [t for t in self._tools if t.name != name]
        self._tool_map.pop(name, None)

    def set_tools(self, tools: List[Tool]) -> None:
        self._tools = list(tools)
        self._tool_map = {t.name: t for t in self._tools}

    async def _inner_loop(
        self,
        messages: List[Message],
    ) -> Tuple[List[Message], int, List[ToolCallTrace], TokenUsage, bool]:
        """Tool execution loop for one outer iteration.

        Returns (final_messages, iterations, tool_traces, usage, hit_max_iterations).
        """
        msgs = list(messages)
        iterations = 0
        tool_traces: List[ToolCallTrace] = []
        total_usage = TokenUsage()
        max_iter = self._loop.max_inner_iterations

        while True:
            while not self._message_queue.empty():
                msgs.append(self._message_queue.get_nowait())

            if max_iter is not None and iterations >= max_iter:
                return msgs, iterations, tool_traces, total_usage, True

            turn = await self._provider.call_once(
                messages=msgs,
                tools=self._tools or None,
                system_prompt=self._system_prompt or None,
            )

            total_usage.input += turn.usage.get("input", 0)
            total_usage.output += turn.usage.get("output", 0)
            total_usage.total += turn.usage.get("total", 0)

            iterations += 1

            if turn.content:
                await _emit(
                    self._callbacks.assistant_message,
                    {"role": "assistant", "content": turn.content},
                )

            if turn.tool_calls:
                msgs.append(
                    {
                        "role": "assistant",
                        "content": turn.content or None,
                        "tool_calls": turn.tool_calls,
                    }
                )
            else:
                msgs.append({"role": "assistant", "content": turn.content})

            if not turn.tool_calls:
                break

            results = await asyncio.gather(*[self._execute_tool_call(tc) for tc in turn.tool_calls])

            for tc, (result, trace) in zip(turn.tool_calls, results, strict=False):
                tool_traces.append(trace)
                msgs.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": result,
                    }
                )
                await _emit(self._callbacks.tool_result, tc["function"]["name"], result)

            await _emit(self._callbacks.iteration_end, iterations, tool_traces)

        return msgs, iterations, tool_traces, total_usage, False

    async def _execute_tool_call(self, tool_call: Message) -> Tuple[str, ToolCallTrace]:
        name = tool_call["function"]["name"]
        arguments = tool_call["function"]["arguments"]

        await _emit(self._callbacks.tool_call, name, arguments)

        t_start = datetime.now()
        tool = self._tool_map.get(name)

        if tool is None:
            error = f"Tool '{name}' not found"
            duration = (datetime.now() - t_start).total_seconds() * 1000
            return error, ToolCallTrace(
                name=name,
                input=arguments,
                output=error,
                duration_ms=duration,
                error=error,
            )

        result = await tool.call(arguments)
        duration = (datetime.now() - t_start).total_seconds() * 1000
        return result, ToolCallTrace(name=name, input=arguments, output=result, duration_ms=duration)


async def _call_verify(verify_fn: List[VerifyFn], messages: List[Message]) -> VerificationRecord:
    """Call each verify_fn in order; return the first failure, or passed if all pass."""
    last: VerificationRecord = VerificationRecord(passed=True)
    for fn in verify_fn:
        if inspect.iscoroutinefunction(fn):
            raw = await fn(messages)
        else:
            raw = fn(messages)

        if isinstance(raw, VerificationRecord):
            record = raw
        elif isinstance(raw, dict):
            record = VerificationRecord(**raw)
        else:
            record = VerificationRecord(passed=bool(raw))

        if not record.passed:
            return record
        last = record
    return last
