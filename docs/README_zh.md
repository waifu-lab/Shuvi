# shuvi

[English](https://github.com/waifu-lab/Shuvi/blob/main/README.md) | [Chinese](https://github.com/waifu-lab/Shuvi/blob/main/docs/README_zh.md)

一個輕量、可擴充的 Python 非同步 agent loop，涵蓋具備工具呼叫能力的對話式 agent、上下文管理、完成度驗證、callback hooks，以及多 agent handoff

---

## 功能特色

- 非同步 agent runtime，支援反覆呼叫 LLM 與執行工具
- 透過 `hydrogen-ai` 支援 tool calling，包含文字與圖片結果
- loop 控制
- 提供 callback hooks


---

## 開發

**安裝**

```bash
# Clone the repo
git clone https://github.com/waifu-lab/Shuvi
cd Shuvi

# Install all workspace dependencies
uv sync
```

**Example**

範例會從目前目錄的 `.env` 讀取 API key：

```bash
pip install shuvi python-dotenv
```

```
OPENAI_API_KEY=sk-...
```

基本用法：

```python
import asyncio
import os

from dotenv import load_dotenv
from hai.providers import create_text_provider
from shuvi.agent import Agent
from shuvi.types import AgentConfig, UserMessage

load_dotenv()


async def main() -> None:
    provider = create_text_provider(
        "openai",
        model="gpt-4o-mini",
        api_key=os.environ["OPENAI_API_KEY"],
        stream=False,
    )
    agent = Agent(
        AgentConfig(
            provider=provider,
            system_prompt="你是一個有幫助的 AI companion",
        )
    )

    result = await agent.run(
        [
            UserMessage(
                content=[
                    {
                        "type": "text",
                        "text": "你好！",
                    }
                ]
            )
        ]
    )
    print(result.messages[-1].content)


asyncio.run(main())
```

如果需要工具：

```python
import asyncio
import os

from dotenv import load_dotenv
from hai.providers import create_text_provider
from hai.tool import tool
from shuvi.agent import Agent
from shuvi.types import AgentConfig, LoopConfig, UserMessage

load_dotenv()


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


async def main() -> None:
    provider = create_text_provider(
        "openai",
        model="gpt-4o-mini",
        api_key=os.environ["OPENAI_API_KEY"],
        stream=False,
    )
    agent = Agent(
        AgentConfig(
            provider=provider,
            system_prompt="你是一個計算助理，必要時可以呼叫工具",
            tools=[add],
            loop=LoopConfig(max_inner_iterations=3),
        )
    )

    result = await agent.run(
        [
            UserMessage(
                content=[
                    {
                        "type": "text",
                        "text": "請幫我計算 123 + 456",
                    }
                ]
            )
        ]
    )
    print(result.messages[-1].content)


asyncio.run(main())
```

如果需要 streaming 模式：

```python
import asyncio
import os

from dotenv import load_dotenv
from hai.providers import create_text_provider
from shuvi.agent import Agent
from shuvi.types import AgentCallbacks, AgentConfig, UserMessage

load_dotenv()


def print_chunk(chunk: str) -> None:
    print(chunk, end="", flush=True)


async def main() -> None:
    provider = create_text_provider(
        "openai",
        model="gpt-4o-mini",
        api_key=os.environ["OPENAI_API_KEY"],
        stream=True,
    )
    agent = Agent(
        AgentConfig(
            provider=provider,
            system_prompt="你是一個有幫助的 AI companion",
            callbacks=AgentCallbacks(on_chunk=print_chunk),
        )
    )

    await agent.run(
        [
            UserMessage(
                content=[
                    {
                        "type": "text",
                        "text": "請用三句話介紹 shuvi",
                    }
                ]
            )
        ]
    )
    print()


asyncio.run(main())
```
