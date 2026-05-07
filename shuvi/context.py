from typing import Awaitable, Callable, List, Optional

from shuvi.types import AppMessage

_LLM_ROLES = {"user", "assistant", "tool"}


async def _default_convert(messages: List[AppMessage]) -> List[AppMessage]:
    return [m for m in messages if m.role in _LLM_ROLES]


class ContextManager:
    """
    Manages app-level message history and the two-step conversion to LLM format.

    transform_context: trim/inject/window at the AppMessage layer before LLM call
    convert_to_llm: filter custom message subtypes, produce the list the LLM sees
    """

    def __init__(
        self,
        transform_context: Optional[Callable[[List[AppMessage]], Awaitable[List[AppMessage]]]] = None,
        convert_to_llm: Optional[Callable[[List[AppMessage]], Awaitable[List[AppMessage]]]] = None,
    ) -> None:
        self._transform = transform_context
        self._convert = convert_to_llm or _default_convert
        self._history: List[AppMessage] = []

    @property
    def history(self) -> List[AppMessage]:
        return self._history

    def append(self, message: AppMessage) -> None:
        self._history.append(message)

    def extend(self, messages: List[AppMessage]) -> None:
        self._history.extend(messages)

    def clear(self) -> None:
        self._history.clear()

    async def prepare(self) -> List[AppMessage]:
        messages = list(self._history)
        if self._transform:
            messages = await self._transform(messages)
        return await self._convert(messages)
