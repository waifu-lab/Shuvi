import asyncio
import os

from dotenv import load_dotenv
from hai.providers.anthropic import AnthropicText
from hai.providers.openai import OpenAI
from hai.tool import tool
from src.agent import Agent
from src.types import AgentCallbacks, AgentConfig, LoopConfig

load_dotenv()


# ── Tools ────────────────────────────────────────────────────────────────────


@tool(
    description="Get the current weather for a city",
    parameters={
        "type": "object",
        "properties": {
            "city": {"type": "string", "description": "City name"},
        },
        "required": ["city"],
    },
)
def get_weather(city: str) -> str:
    return "台北市目前天氣：晴天，25°C，濕度 60%"


@tool(
    description="Add two numbers together",
    parameters={
        "type": "object",
        "properties": {
            "a": {"type": "number"},
            "b": {"type": "number"},
        },
        "required": ["a", "b"],
    },
)
def add(a: float, b: float) -> float:
    return a + b


@tool(
    description="Multiply two numbers",
    parameters={
        "type": "object",
        "properties": {
            "a": {"type": "number"},
            "b": {"type": "number"},
        },
        "required": ["a", "b"],
    },
)
def multiply(a: float, b: float) -> float:
    return a * b


@tool(
    description="Read the content of a file by its path",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "File path"},
        },
        "required": ["path"],
    },
)
def read_file(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return f"Error: file '{path}' not found"


@tool(
    description="Write content to a file",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "File path"},
            "content": {"type": "string", "description": "Content to write"},
        },
        "required": ["path", "content"],
    },
)
def write_file(path: str, content: str) -> str:
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return f"Written {len(content)} chars to '{path}'"


# ── Helpers ───────────────────────────────────────────────────────────────────


def build_provider():
    provider_name = os.getenv("PROVIDER", "openai").lower()
    model = os.getenv("MODEL")

    if provider_name == "anthropic":
        return AnthropicText(
            api_key=os.environ["ANTHROPIC_API_KEY"],
            model=model or "claude-sonnet-4-5",
            stream=True,
        )
    else:
        return OpenAI(
            api_key=os.environ["OPENAI_API_KEY"],
            model=model or "gpt-4o-mini",
            stream=True,
        )


def print_result(result):
    print("\n" + "─" * 50)
    print(f"Outcome   : {result.outcome}")
    print(f"Duration  : {result.trace.duration_ms:.0f} ms")
    print(f"Tokens    : {result.trace.token_usage}")
    print(f"Iterations: {result.trace.inner_iterations}")
    if result.trace.tool_calls:
        print("Tool calls:")
        for tc in result.trace.tool_calls:
            status = f" ⚠ {tc.error}" if tc.error else ""
            print(f"  • {tc.name} ({tc.duration_ms:.0f} ms){status}")


def make_callbacks():
    return AgentCallbacks(
        tool_call=lambda name, args: print(f"\n[tool_call] {name}({args})"),
        tool_result=lambda name, result: print(f"[tool_result] {name} → {result}"),
        error=lambda e: print(f"[error] {e}"),
    )


# ── Test 1: 基本工具（原有） ────────────────────────────────────────────────


async def test_agent():
    """Original smoke test: weather + addition in one shot."""
    provider = build_provider()

    config = AgentConfig(
        provider=provider,
        system_prompt="你是一個有用的助理，可以查天氣和做計算。回覆請使用繁體中文。",
        tools=[get_weather, add],
        loop=LoopConfig(max_inner_iterations=10),
        callbacks=make_callbacks(),
    )

    agent = Agent(config)

    messages = [
        {
            "role": "user",
            "content": "台北現在的天氣如何？另外幫我算 123 + 456 是多少？",
        },
    ]

    print(f"\n{'=' * 50}")
    print("Test 1 – 基本工具呼叫")
    print(f"Provider: {provider.name} / {provider.model}")
    print("─" * 50)

    result = await agent.run(messages)
    print_result(result)

    assert result.outcome.value in ("completed", "max_iterations")
    assert len(result.trace.tool_calls) >= 2, "應至少呼叫 2 個工具"
    print("✓ test_agent passed\n")


# ── Test 2: 多次工具存取 ────────────────────────────────────────────────────


async def test_multiple_tool_calls():
    """Agent must call tools multiple times in sequence to fulfil a chained request."""
    provider = build_provider()

    config = AgentConfig(
        provider=provider,
        system_prompt=(
            "你是一個計算助理。使用者要求多步驟計算時，請依序呼叫工具完成每一步，並在最後用繁體中文總結計算過程與結果。"
        ),
        tools=[add, multiply],
        loop=LoopConfig(max_inner_iterations=15),
        callbacks=make_callbacks(),
    )

    agent = Agent(config)

    # Requires: add(3, 4) → 7, then multiply(7, 6) → 42
    messages = [
        {
            "role": "user",
            "content": "請幫我計算 (3 + 4) × 6，分兩步完成：先加法再乘法。",
        }
    ]

    print(f"\n{'=' * 50}")
    print("Test 2 – 多次工具存取（鏈式計算）")
    print("─" * 50)

    result = await agent.run(messages)
    print_result(result)

    assert result.outcome.value in ("completed", "max_iterations")
    assert len(result.trace.tool_calls) >= 2, "應至少呼叫 2 次工具"
    tool_names = [tc.name for tc in result.trace.tool_calls]
    assert "add" in tool_names, "應有加法工具呼叫"
    assert "multiply" in tool_names, "應有乘法工具呼叫"
    print("✓ test_multiple_tool_calls passed\n")


# ── Test 3: 編寫簡易程式 ────────────────────────────────────────────────────


async def test_write_program():
    """Agent writes a Python script to disk and then reads it back to verify."""
    import pathlib
    import tempfile

    provider = build_provider()

    with tempfile.TemporaryDirectory() as tmpdir:
        target = str(pathlib.Path(tmpdir) / "hello.py")

        config = AgentConfig(
            provider=provider,
            system_prompt=(
                "你是一個程式助理。使用者請你產生 Python 程式碼並存檔，"
                "完成後請用 read_file 確認檔案內容，再回覆使用者。"
                "程式碼請只包含純 Python，不需要 markdown 區塊。"
            ),
            tools=[write_file, read_file],
            loop=LoopConfig(max_inner_iterations=10),
            callbacks=make_callbacks(),
        )

        agent = Agent(config)

        messages = [
            {
                "role": "user",
                "content": (
                    f"請幫我寫一個 Python 程式，計算 1 到 10 的總和並印出結果，存到 {target}，然後讀取並確認內容。"
                ),
            }
        ]

        print(f"\n{'=' * 50}")
        print("Test 3 – 編寫簡易程式（write + read）")
        print("─" * 50)

        result = await agent.run(messages)
        print_result(result)

        assert result.outcome.value in ("completed", "max_iterations")
        tool_names = [tc.name for tc in result.trace.tool_calls]
        assert "write_file" in tool_names, "應呼叫 write_file"
        assert "read_file" in tool_names, "應呼叫 read_file"
        assert pathlib.Path(target).exists(), "程式檔案應已建立"
        print("✓ test_write_program passed\n")


# ── Test 4: 使用者中途輸入文字 ──────────────────────────────────────────────


async def test_user_mid_conversation():
    """Inject a user message via queue_message while the agent is running."""
    provider = build_provider()

    received_messages: list[str] = []

    def on_iteration_end(iterations: int, tool_calls):
        print(f"[iteration_end] iter={iterations}")

    config = AgentConfig(
        provider=provider,
        system_prompt=("你是一個計算助理，使用繁體中文回覆。每次收到新指令時，請先確認收到，再執行計算。"),
        tools=[add, multiply],
        loop=LoopConfig(max_inner_iterations=20),
        callbacks=AgentCallbacks(
            tool_call=lambda name, args: print(f"\n[tool_call] {name}({args})"),
            tool_result=lambda name, result: print(f"[tool_result] {name} → {result}"),
            error=lambda e: print(f"[error] {e}"),
            iteration_end=on_iteration_end,
            assistant_message=lambda msg: received_messages.append(msg.get("content", "")),
        ),
    )

    agent = Agent(config)

    # Initial request
    messages = [{"role": "user", "content": "請幫我算 10 + 20。"}]

    print(f"\n{'=' * 50}")
    print("Test 4 – 使用者中途輸入文字（queue_message）")
    print("─" * 50)

    # Schedule a follow-up user message to be injected after a short delay
    async def inject_later():
        await asyncio.sleep(0.5)
        print("\n[inject] 使用者中途送出新訊息：請再算 3 × 7")
        agent.queue_message({"role": "user", "content": "另外請再算 3 × 7 是多少？"})

    result, _ = await asyncio.gather(agent.run(messages), inject_later())
    print_result(result)

    assert result.outcome.value in ("completed", "max_iterations")
    # The queued message should have been consumed; tool calls should include multiply
    tool_names = [tc.name for tc in result.trace.tool_calls]
    print(f"Tool calls performed: {tool_names}")
    print("✓ test_user_mid_conversation passed\n")


# ── Entry point ───────────────────────────────────────────────────────────────

TESTS = {
    "1": ("基本工具呼叫", test_agent),
    "2": ("多次工具存取", test_multiple_tool_calls),
    "3": ("編寫簡易程式", test_write_program),
    "4": ("使用者中途輸入", test_user_mid_conversation),
}


async def run_all():
    for key, (name, fn) in TESTS.items():
        print(f"\n▶ Running test {key}: {name}")
        await fn()
    print("\n✅ All tests passed")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        key = sys.argv[1]
        if key not in TESTS:
            print(f"Unknown test '{key}'. Choose from: {list(TESTS.keys())}")
            sys.exit(1)
        name, fn = TESTS[key]
        print(f"▶ Running test {key}: {name}")
        asyncio.run(fn())
    else:
        asyncio.run(run_all())
