from enum import Enum
from typing import (
    Any,
    Awaitable,
    Callable,
    Dict,
    List,
    Literal,
    Optional,
    Protocol,
    Sequence,
    Union,
    runtime_checkable,
)

from hai.providers.providers import ProviderText
from hai.tool import Tool
from pydantic import BaseModel, ConfigDict, Field


class ToolCallFunction(BaseModel):
    name: str
    arguments: str


class ToolCall(BaseModel):
    id: str
    type: Literal["function"] = "function"
    function: ToolCallFunction


@runtime_checkable
class AppMessage(Protocol):
    @property
    def role(self) -> str: ...
    @property
    def content(self) -> Any: ...

    def model_dump(self, *, exclude_none: bool = False) -> Dict[str, Any]: ...


class UserMessage(BaseModel):
    role: Literal["user"] = "user"
    content: List[Dict[str, Any]]

    def model_dump(self, *, exclude_none: bool = False) -> Dict[str, Any]:
        return {"role": self.role, "content": self.content}


class AssistantMessage(BaseModel):
    role: Literal["assistant"] = "assistant"
    content: Optional[str] = None
    tool_calls: Optional[List[ToolCall]] = None


class ToolMessage(BaseModel):
    role: Literal["tool"] = "tool"
    content: str
    tool_call_id: str


class SystemMessage(BaseModel):
    role: Literal["system"] = "system"
    content: str


LLMMessage = Union[UserMessage, AssistantMessage, ToolMessage]


class AGENT_EVENT(str, Enum):
    agent_start = "agent_start"
    agent_end = "agent_end"
    tool_start = "tool_start"
    tool_end = "tool_end"
    message_update = "message_update"
    context_building = "context_building"
    context_building_end = "context_building_end"
    context_compacting = "context_compacting"


class AGENT_OUTCOME(str, Enum):
    completed = "completed"
    max_iterations = "max_iterations"
    error = "error"
    verify_failed = "verify_failed"


class ToolCallTrace(BaseModel):
    name: str
    input: str
    output: str
    duration_ms: float
    error: Optional[str] = None


class VerificationRecord(BaseModel):
    passed: bool
    reason: Optional[str] = None


class TokenUsage(BaseModel):
    input: int = 0
    output: int = 0
    total: int = 0


class ExecutionTrace(BaseModel):
    start_time: str
    end_time: str = ""
    duration_ms: float = 0.0
    token_usage: TokenUsage = Field(default_factory=TokenUsage)
    inner_iterations: int = 0
    outer_retries: int = 0
    outcome: AGENT_OUTCOME = AGENT_OUTCOME.completed
    tool_calls: List[ToolCallTrace] = []
    verifications: List[VerificationRecord] = []
    session_id: Optional[str] = None


class AgentResult(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    messages: List[AppMessage]
    trace: ExecutionTrace
    outcome: AGENT_OUTCOME
    handoff: Optional[str] = None


class HandoffSignal(Exception):
    """Raised inside Agent to signal control transfer to another agent."""

    def __init__(self, target: str, context: Optional[str] = None) -> None:
        self.target = target
        self.context = context  # optional summary passed to the next agent


VerifyResult = Union[VerificationRecord, bool]
VerifyFn = Union[
    Callable[[Sequence[AppMessage]], VerifyResult],
    Callable[[Sequence[AppMessage]], "Awaitable[VerifyResult]"],
]


class LoopState(BaseModel):
    """Mutable state carried across iterations of the agent loop."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    turn_count: int = 0
    pending_summary: Optional[str] = None  # accumulated summary for context compaction
    stop_active: bool = False  # a stop hook / signal has fired
    transition: Optional[str] = None  # handoff target agent name


class LoopConfig(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    max_inner_iterations: Optional[int] = None  # None = unlimited
    max_outer_retries: int = 3
    verify_completion: Optional[List[VerifyFn]] = None  # fn(messages) -> VerificationRecord | bool


class AgentCallbacks(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    tool_call: Optional[Callable[[str, str], None]] = None
    tool_result: Optional[Callable[[str, str], None]] = None
    assistant_message: Optional[Callable[[AppMessage], None]] = None
    on_chunk: Optional[Union[Callable[[str], None], Callable[[str], Awaitable[None]]]] = (
        None  # called per streaming token
    )
    iteration_end: Optional[Callable[[int, List[ToolCallTrace]], None]] = None
    error: Optional[Callable[[Exception], None]] = None
    state_update: Optional[Callable[["LoopState"], None]] = None  # fired after each state mutation


class AgentConfig(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    provider: ProviderText
    system_prompt: str = ""
    tools: List[Tool] = []
    loop: LoopConfig = LoopConfig()
    callbacks: AgentCallbacks = AgentCallbacks()
    session_id: Optional[str] = None
    context_manager: Optional[Any] = None  # shuvi.context.ContextManager; Any avoids circular import
