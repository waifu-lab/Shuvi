import asyncio
import base64
import inspect
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Sequence, Tuple, Union

from hai.providers.providers import ProviderText
from hai.tool import ImageResult, Tool

from shuvi.types import (
    AGENT_OUTCOME,
    AgentCallbacks,
    AgentConfig,
    AgentResult,
    AppMessage,
    AssistantMessage,
    ExecutionTrace,
    HandoffSignal,
    LoopConfig,
    LoopState,
    TokenUsage,
    ToolCall,
    ToolCallFunction,
    ToolCallTrace,
    ToolMessage,
    UserMessage,
    VerificationRecord,
    VerifyFn,
)

if TYPE_CHECKING:
    from shuvi.context import ContextManager


async def _emit(fn: Optional[Any], *args: Any) -> None:
    if fn is None:
        return
    if inspect.iscoroutinefunction(fn):
        await fn(*args)
    else:
        result = fn(*args)
        if asyncio.iscoroutine(result):
            await result


def _to_llm(messages: Sequence[AppMessage]) -> List[Dict[str, Any]]:
    return [m.model_dump(exclude_none=True) for m in messages]


class Agent:
    def __init__(self, config: AgentConfig) -> None:
        self._provider: ProviderText = config.provider
        self._system_prompt: str = config.system_prompt
        self._loop: LoopConfig = config.loop
        self._callbacks: AgentCallbacks = config.callbacks
        self._session_id: Optional[str] = config.session_id
        self._tools: List[Tool] = list(config.tools)
        self._tool_map: Dict[str, Tool] = {t.name: t for t in self._tools}
        self._message_queue: asyncio.Queue[AppMessage] = asyncio.Queue()
        self._context_manager: Optional["ContextManager"] = config.context_manager
        self._state = LoopState()

    @property
    def state(self) -> LoopState:
        return self._state

    def reset_state(self) -> None:
        self._state = LoopState()

    async def run(self, messages: Optional[Sequence[AppMessage]] = None) -> AgentResult:
        """
        If ContextManager is present, messages param is ignored — append to
        context_manager before calling run(). Otherwise messages must be provided.
        """
        if self._context_manager is not None:
            initial_messages = await self._context_manager.prepare()
        else:
            if messages is None:
                raise ValueError("messages required when no ContextManager is configured")
            initial_messages = list(messages)

        start = datetime.now()
        trace = ExecutionTrace(
            start_time=start.isoformat(),
            session_id=self._session_id,
        )

        current_messages = initial_messages
        verify_fn = self._loop.verify_completion
        max_outer = self._loop.max_outer_retries
        handoff_target: Optional[str] = None

        try:
            while True:
                try:
                    final_msgs, iterations, tool_traces, usage, hit_max = await self._inner_loop(current_messages)
                except HandoffSignal as hs:
                    handoff_target = hs.target
                    self._state.transition = hs.target
                    await _emit(self._callbacks.state_update, self._state)
                    trace.outcome = AGENT_OUTCOME.completed
                    final_msgs = current_messages
                    break

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
                    UserMessage(content=[{"type": "text", "text": f"驗證未通過：{verification.reason}，請修正"}])
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

        if self._context_manager is not None:
            new_msgs = final_msgs[len(initial_messages) :]
            self._context_manager.extend(new_msgs)

        return AgentResult(messages=final_msgs, trace=trace, outcome=trace.outcome, handoff=handoff_target)

    def queue_message(self, message: AppMessage) -> None:
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
        messages: Sequence[AppMessage],
    ) -> Tuple[List[AppMessage], int, List[ToolCallTrace], TokenUsage, bool]:
        msgs: List[AppMessage] = list(messages)
        iterations = 0
        tool_traces: List[ToolCallTrace] = []
        total_usage = TokenUsage()
        max_iter = self._loop.max_inner_iterations

        while True:
            while not self._message_queue.empty():
                msgs.append(self._message_queue.get_nowait())

            if self._state.stop_active:
                return msgs, iterations, tool_traces, total_usage, False

            if max_iter is not None and iterations >= max_iter:
                return msgs, iterations, tool_traces, total_usage, True

            turn = await self._provider.call_once(
                messages=_to_llm(msgs),
                tools=self._tools or None,
                system_prompt=self._system_prompt or None,
                on_chunk=self._callbacks.on_chunk,
            )

            total_usage.input += turn.usage.get("input", 0)
            total_usage.output += turn.usage.get("output", 0)
            total_usage.total += turn.usage.get("total", 0)

            self._state.turn_count += 1
            iterations += 1
            await _emit(self._callbacks.state_update, self._state)

            if turn.content:
                await _emit(
                    self._callbacks.assistant_message,
                    AssistantMessage(content=turn.content),
                )

            tool_calls: Optional[List[ToolCall]] = None
            if turn.tool_calls:
                tool_calls = [
                    ToolCall(
                        id=tc["id"],
                        function=ToolCallFunction(name=tc["function"]["name"], arguments=tc["function"]["arguments"]),
                    )
                    for tc in turn.tool_calls
                ]
                msgs.append(AssistantMessage(content=turn.content, tool_calls=tool_calls))
            else:
                msgs.append(AssistantMessage(content=turn.content))

            if not tool_calls:
                break

            results = await asyncio.gather(*[self._execute_tool_call(tc) for tc in tool_calls])

            for tc, (result, trace) in zip(tool_calls, results, strict=False):
                tool_traces.append(trace)
                # Sent tool result as User message content
                if isinstance(result, ImageResult):
                    msgs.append(ToolMessage(tool_call_id=tc.id, content="[image result]"))
                    msgs.append(
                        UserMessage(
                            content=[
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:{result.media_type};base64,{base64.b64encode(result.data).decode()}"
                                    },
                                }
                            ]
                        )
                    )
                    result_str = result.description or f"[image {len(result.data)} bytes]"
                    await _emit(self._callbacks.tool_result, tc.function.name, result_str)
                else:
                    msgs.append(ToolMessage(tool_call_id=tc.id, content=result))
                    await _emit(self._callbacks.tool_result, tc.function.name, result)

            await _emit(self._callbacks.iteration_end, iterations, tool_traces)

        return msgs, iterations, tool_traces, total_usage, False

    async def _execute_tool_call(self, tool_call: ToolCall) -> Tuple[Union[str, ImageResult], ToolCallTrace]:
        name = tool_call.function.name
        arguments = tool_call.function.arguments

        await _emit(self._callbacks.tool_call, name, arguments)

        t_start = datetime.now()
        tool = self._tool_map.get(name)

        if tool is None:
            error = f"Tool '{name}' not found"
            duration = (datetime.now() - t_start).total_seconds() * 1000
            return error, ToolCallTrace(name=name, input=arguments, output=error, duration_ms=duration, error=error)

        try:
            result = await tool.call(arguments)
        except Exception as e:
            duration = (datetime.now() - t_start).total_seconds() * 1000
            error_msg = f"Error executing tool '{name}': {e}"
            await _emit(self._callbacks.on_tool_error, name, e)
            return error_msg, ToolCallTrace(
                name=name, input=arguments, output=error_msg, duration_ms=duration, error=error_msg
            )
        duration = (datetime.now() - t_start).total_seconds() * 1000
        if isinstance(result, ImageResult):
            trace_output = result.description or f"[image {len(result.data)} bytes]"
        else:
            trace_output = result
        return result, ToolCallTrace(name=name, input=arguments, output=trace_output, duration_ms=duration)


async def _call_verify(verify_fn: List[VerifyFn], messages: Sequence[AppMessage]) -> VerificationRecord:
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
