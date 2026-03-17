from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union

from hai.providers.providers import ProviderText
from hai.tool import Tool
from pydantic import BaseModel, ConfigDict


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
    input: Any
    output: Any
    duration_ms: float
    error: Optional[str] = None


class VerificationRecord(BaseModel):
    passed: bool
    reason: Optional[str] = None


class ExecutionTrace(BaseModel):
    start_time: str
    end_time: str = ""
    duration_ms: float = 0.0
    token_usage: Dict[str, int] = {"input": 0, "output": 0, "total": 0}
    inner_iterations: int = 0
    outer_retries: int = 0
    outcome: AGENT_OUTCOME = AGENT_OUTCOME.completed
    tool_calls: List[ToolCallTrace] = []
    verifications: List[VerificationRecord] = []
    session_id: Optional[str] = None


class AgentResult(BaseModel):
    messages: List[Dict[str, Any]]
    trace: ExecutionTrace
    outcome: AGENT_OUTCOME


VerifyFn = Callable[[List[Dict[str, Any]]], VerificationRecord]


class LoopConfig(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    max_inner_iterations: Optional[int] = None  # None = unlimited
    max_outer_retries: int = 3
    verify_completion: Optional[list[VerifyFn]] = None  # fn(messages) -> VerificationRecord


class AgentCallbacks(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    tool_call: Optional[Callable[[str, Any], None]] = None
    tool_result: Optional[Callable[[str, str], None]] = None
    assistant_message: Optional[Callable[[Dict[str, Any]], None]] = None
    iteration_end: Optional[Callable[[int, List[ToolCallTrace]], None]] = None
    error: Optional[Callable[[Exception], None]] = None


class AgentConfig(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    provider: ProviderText
    system_prompt: str = ""
    tools: List[Tool] = []
    loop: LoopConfig = LoopConfig()
    callbacks: AgentCallbacks = AgentCallbacks()
    session_id: Optional[str] = None
