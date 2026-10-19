# shuvi

[English](https://github.com/waifu-lab/Shuvi/blob/main/README.md) | [Chinese](https://github.com/waifu-lab/Shuvi/blob/main/docs/README_zh.md)

A lightweight, extensible async agent loop for building AI companions with Python. `shuvi` covers tool-using conversational agents, context management, completion verification, callbacks, and multi-agent handoffs.

---

## Features

- Async agent runtime for iterative LLM calls and tool execution.
- Tool calling support through `hydrogen-ai`, including text and image results.
- Configurable loop controls for max iterations, retries, and completion verification.
- Callback hooks for streaming chunks, assistant messages, tool calls, tool results, errors, and state updates.


---

## Development

**Setup**

```bash
# Clone the repo
git clone https://github.com/waifu-lab/Shuvi
cd Shuvi

# Install all workspace dependencies
uv sync
```

**Example**

The examples read the API key from a `.env` file in the working directory:

```bash
pip install shuvi
```

```
OPENAI_API_KEY=sk-...
```

Basic usage:

```python
import asyncio
import os


from hai.providers import create_text_provider
from shuvi.agent import Agent
from shuvi.types import AgentConfig, UserMessage

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
            system_prompt="You are a helpful AI companion.",
        )
    )

    result = await agent.run(
        [
            UserMessage(
                content=[
                    {
                        "type": "text",
                        "text": "Hello!",
                    }
                ]
            )
        ]
    )
    print(result.messages[-1].content)


asyncio.run(main())
```

With tools:

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
            system_prompt="You are a calculator assistant. Use tools when needed.",
            tools=[add],
            loop=LoopConfig(max_inner_iterations=10),
        )
    )

    result = await agent.run(
        [
            UserMessage(
                content=[
                    {
                        "type": "text",
                        "text": "Please calculate 123 + 456.",
                    }
                ]
            )
        ]
    )
    print(result.messages[-1].content)


asyncio.run(main())
```

Streaming mode:

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
            system_prompt="You are a helpful AI companion.",
            callbacks=AgentCallbacks(on_chunk=print_chunk),
        )
    )

    await agent.run(
        [
            UserMessage(
                content=[
                    {
                        "type": "text",
                        "text": "Introduce shuvi in three sentences.",
                    }
                ]
            )
        ]
    )
    print()


asyncio.run(main())
```

**Testing**

```bash
uv run pytest
```
