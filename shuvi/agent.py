import asyncio
import base64
import inspect
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Sequence, Tuple, Union

from hai.providers.providers import ProviderText, StreamInterruptedError, TurnResult
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


def _parse_tool_calls(turn: TurnResult) -> Optional[List[ToolCall]]:
    if not turn.tool_calls or turn.finish_reason == "length":
        return None
    return [
        ToolCall(
            id=tc["id"],
            function=ToolCallFunction(name=tc["function"]["name"], arguments=tc["function"]["arguments"]),
        )
        for tc in turn.tool_calls
    ]


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
        self._pending_handoff: Optional[HandoffSignal] = None

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
        self._pending_handoff = None
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
                    final_msgs = hs.messages if hs.messages is not None else current_messages
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

                prompt = self._loop.verify_retry_prompt.format(reason=verification.reason)
                current_messages = final_msgs + [UserMessage(content=[{"type": "text", "text": prompt}])]

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
        continuations = 0
        # last message is the synthetic "continue" prompt after a finish_reason="length" turn
        continuing = False

        while True:
            if not continuing:
                while not self._message_queue.empty():
                    msgs.append(self._message_queue.get_nowait())

            if self._state.stop_active or (max_iter is not None and iterations >= max_iter):
                if continuing:
                    msgs.pop()
                return msgs, iterations, tool_traces, total_usage, not self._state.stop_active

            turn = await self._call_turn(msgs)

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

            truncated = turn.finish_reason == "length"
            tool_calls = _parse_tool_calls(turn)

            content = turn.content
            if continuing:
                msgs.pop()  # synthetic continue prompt
                content = (msgs.pop().content or "") + content
                continuing = False
            msgs.append(AssistantMessage(content=content, tool_calls=tool_calls))

            if truncated and continuations < self._loop.max_length_continuations:
                continuations += 1
                prompt = (
                    self._loop.truncated_tool_call_prompt if turn.tool_calls else self._loop.length_continuation_prompt
                )
                msgs.append(UserMessage(content=[{"type": "text", "text": prompt}]))
                continuing = True
                continue

            if not tool_calls:
                break

            await self._run_tools(tool_calls, msgs, tool_traces)
            await _emit(self._callbacks.iteration_end, iterations, tool_traces)

        return msgs, iterations, tool_traces, total_usage, False

    async def _run_tools(
        self, tool_calls: List[ToolCall], msgs: List[AppMessage], tool_traces: List[ToolCallTrace]
    ) -> None:
        """Execute tool calls in parallel and append their results to msgs; raises a pending handoff."""
        results = await asyncio.gather(*[self._execute_tool_call(tc) for tc in tool_calls])

        # Image messages are deferred so every ToolMessage directly follows the assistant tool_calls
        image_msgs: List[AppMessage] = []
        for tc, (result, trace) in zip(tool_calls, results, strict=False):
            tool_traces.append(trace)
            # Send image tool result as User message content
            if isinstance(result, ImageResult):
                msgs.append(ToolMessage(tool_call_id=tc.id, content="[image result]"))
                image_msgs.append(
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
        msgs.extend(image_msgs)

        if self._pending_handoff is not None:
            handoff, self._pending_handoff = self._pending_handoff, None
            handoff.messages = msgs
            raise handoff

    async def _call_turn(self, msgs: Sequence[AppMessage]) -> TurnResult:
        stream_retries = 0
        empty_retries = 0
        usage = {"input": 0, "output": 0, "total": 0}  # summed over discarded attempts too
        while True:
            try:
                turn = await self._provider.call_once(
                    messages=_to_llm(msgs),
                    tools=self._tools or None,
                    system_prompt=self._system_prompt or None,
                    on_chunk=self._callbacks.on_chunk,
                )
            except StreamInterruptedError as e:
                if stream_retries >= self._loop.max_turn_retries:
                    raise
                stream_retries += 1
                await _emit(self._callbacks.on_stream_reset, e.partial_content)
                continue

            for key in usage:
                usage[key] += turn.usage.get(key, 0)

            empty = not turn.content and not turn.tool_calls and turn.finish_reason != "content_filter"
            if empty and empty_retries < self._loop.max_empty_retries:
                empty_retries += 1
                continue
            return turn.model_copy(update={"usage": usage})

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
            # invoke() raises instead of returning an error string, so errors reach on_tool_error and the trace
            result = await tool.invoke(arguments)
        except HandoffSignal as hs:
            # the tool_call still needs a ToolMessage; the signal is re-raised after this turn's results
            if self._pending_handoff is None:
                self._pending_handoff = hs
            result = f"Handing off to agent '{hs.target}'"
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
