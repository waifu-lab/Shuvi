import { createFileRoute, Link } from "@tanstack/react-router";
import { HomeLayout } from "fumadocs-ui/layouts/home";
import { ArrowRight, Check, Copy } from "lucide-react";
import { useState } from "react";
import { PythonCode } from "@/components/code";
import { SchwiCore } from "@/components/schwi-core";
import { baseOptions } from "@/lib/layout.shared";
import { gitConfig } from "@/lib/shared";

export const Route = createFileRoute("/")({
  component: Home,
  head: () => ({
    meta: [
      { title: "Shuvi" },
      {
        name: "description",
        content:
          "A lightweight async agent loop for building AI companions with Python.",
      },
    ],
  }),
});

const githubUrl = `https://github.com/${gitConfig.user}/${gitConfig.repo}`;

const heroCode = `from hai.providers import create_text_provider
from shuvi.agent import Agent
from shuvi.types import AgentConfig, UserMessage

llm = create_text_provider("openai", model="gpt-4o-mini")
schwi = Agent(AgentConfig(
    provider=llm,
    system_prompt="你是修比，一個想理解「心」的機凱種。",
))

result = await schwi.run([
    UserMessage(content=[{"type": "text", "text": "心，是什麼？"}]),
])
print(result.messages[-1].content)`;

const toolCode = `@tool
def scan(target: str) -> str:
    """解析目標，回傳結果。"""
    return f"{target}：解析完成"


schwi = Agent(AgentConfig(
    provider=llm,
    tools=[scan],
    loop=LoopConfig(max_inner_iterations=10),
))`;

const verifyCode = `def has_answer(messages) -> VerificationRecord:
    text = messages[-1].content or ""
    if "結論" in text:
        return VerificationRecord(passed=True)
    return VerificationRecord(passed=False, reason="請在最後寫出結論")


loop = LoopConfig(verify_completion=[has_answer], max_outer_retries=3)`;

const swarmCode = `@tool
def to_riku(reason: str) -> str:
    """把對話交給策士。"""
    raise HandoffSignal("riku", context=reason)


swarm = Swarm({"schwi": schwi, "riku": riku})
result = await swarm.run("schwi", messages)`;

const callbacks = [
  { name: "on_chunk", desc: "串流的每一個字" },
  { name: "tool_call", desc: "要呼叫哪個工具" },
  { name: "tool_result", desc: "工具回了什麼" },
  { name: "on_tool_error", desc: "工具出錯了" },
  { name: "state_update", desc: "LoopState 改變了" },
  { name: "iteration_end", desc: "一輪工具跑完" },
];

function CopyCommand({ command }: { command: string }) {
  const [copied, setCopied] = useState(false);

  async function copy() {
    try {
      await navigator.clipboard.writeText(command);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // 剪貼簿不可用時，使用者仍可手動選取文字
    }
  }

  return (
    <div className="inline-flex max-w-full items-center gap-3 rounded-lg border bg-fd-card px-4 py-2.5 font-mono text-sm">
      <span className="select-none text-fd-muted-foreground">$</span>
      <code className="truncate">{command}</code>
      <button
        type="button"
        onClick={copy}
        aria-label={copied ? "Copied" : "Copy install command"}
        className="text-fd-muted-foreground transition-colors hover:text-fd-foreground"
      >
        {copied ? <Check className="size-4" /> : <Copy className="size-4" />}
      </button>
    </div>
  );
}

function DocLink({
  href,
  className,
  children,
}: {
  href: string;
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <Link to="/docs/$" params={{ _splat: href }} className={className}>
      {children}
    </Link>
  );
}

function Feature({
  index,
  title,
  href,
  children,
  description,
}: {
  index: string;
  title: string;
  href: string;
  description: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <section className="border-t py-14 md:py-20">
      <div className="max-w-2xl">
        <div className="font-mono text-xs tracking-widest text-fd-primary">
          {index}
        </div>
        <h2 className="mt-2 text-2xl font-bold tracking-tight md:text-3xl">
          {title}
        </h2>
        <p className="mt-3 text-fd-muted-foreground">{description}</p>
        <DocLink
          href={href}
          className="mt-3 inline-flex items-center gap-1 text-sm font-medium text-fd-primary hover:underline"
        >
          閱讀文件
          <ArrowRight className="size-4" />
        </DocLink>
      </div>
      <div className="mt-8 min-w-0">{children}</div>
    </section>
  );
}

function Home() {
  return (
    <HomeLayout {...baseOptions()} links={[{ text: "文件", url: "/docs" }]}>
      <div className="relative">
        <div className="circuit-grid pointer-events-none absolute inset-x-0 top-0 h-[640px]" />
        <main className="relative mx-auto w-full max-w-6xl px-4 md:px-6">
          <section className="grid grid-cols-1 items-center gap-10 py-14 md:py-20 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)]">
            <div>
              <div className="inline-flex items-center gap-2 rounded-full border border-fd-primary/40 bg-fd-primary/10 px-3 py-1 font-mono text-xs text-fd-primary">
                <span className="size-1.5 rounded-full bg-fd-primary motion-safe:animate-pulse" />
                Ex-Machina · Üc207Pr4f57t9
              </div>
              <h1 className="mt-5 text-5xl font-extrabold tracking-tight md:text-6xl">
                Shuvi
                <span className="ml-3 align-middle text-2xl font-bold text-fd-primary md:text-3xl">
                  シュヴィ
                </span>
              </h1>
              <p className="mt-4 max-w-lg text-lg text-fd-muted-foreground">
                用 Python 打造 AI 夥伴的輕量非同步 agent loop。
              </p>
              <p className="mt-2 max-w-lg text-sm text-fd-muted-foreground">
                呼叫模型、執行工具、驗證結果、交棒給下一個 agent。
                就像修比一樣，一圈一圈地解析，直到理解為止。
              </p>
              <div className="mt-8 flex flex-wrap gap-3">
                <DocLink
                  href="quick-start"
                  className="inline-flex items-center gap-2 rounded-full bg-fd-primary px-5 py-2.5 text-sm font-medium text-fd-primary-foreground shadow-lg shadow-fd-primary/25 transition-opacity hover:opacity-90"
                >
                  開始使用
                  <ArrowRight className="size-4" />
                </DocLink>
                <DocLink
                  href=""
                  className="inline-flex items-center gap-2 rounded-full border px-5 py-2.5 text-sm font-medium transition-colors hover:bg-fd-accent"
                >
                  專案概覽
                </DocLink>
              </div>
              <div className="mt-6">
                <CopyCommand command="pip install shuvi" />
              </div>
            </div>
            <SchwiCore className="mx-auto w-full max-w-75 motion-safe:animate-[schwi-float_6s_ease-in-out_infinite] sm:max-w-100 lg:max-w-130" />
          </section>

          <Feature
            index="01 · 起動"
            title="一個 Agent，一次 run()。"
            href="agent"
            description={
              <>
                給 Agent 一個 hai 的文字模型和 system
                prompt，丟進訊息就會開始思考。
                模型要工具就跑工具，跑完再問模型，直到它不再需要工具為止。
              </>
            }
          >
            <PythonCode code={heroCode} />
          </Feature>

          <Feature
            index="02 · 道具"
            title="函式就是工具。"
            href="tools"
            description="工具直接用 hydrogen-ai 的 @tool。同一輪的多個工具呼叫會並行執行，出錯的工具會把錯誤字串交回模型，不會讓整個 loop 停下來。"
          >
            <PythonCode code={toolCode} />
          </Feature>

          <Feature
            index="03 · 檢證"
            title="沒過驗證，就再想一次。"
            href="verification"
            description="loop 結束後跑你寫的驗證函式。沒過就把理由當成新訊息塞回去，讓模型重來，最多 max_outer_retries 次。"
          >
            <PythonCode code={verifyCode} />
          </Feature>

          <Feature
            index="04 · 觀測"
            title="每一步都看得到。"
            href="callbacks"
            description="串流文字、工具呼叫、錯誤、狀態變化都有 callback，同步或 async 函式都可以。跑完還有一份 ExecutionTrace 記錄用了多少 token、呼叫了哪些工具。"
          >
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {callbacks.map((cb) => (
                <div
                  key={cb.name}
                  className="min-w-0 rounded-xl border bg-fd-card p-4 transition-colors hover:border-fd-primary/50"
                >
                  <code className="block truncate font-mono text-sm text-fd-primary">
                    {cb.name}
                  </code>
                  <div className="mt-1 text-xs text-fd-muted-foreground">
                    {cb.desc}
                  </div>
                </div>
              ))}
            </div>
          </Feature>

          <Feature
            index="05 · 連結"
            title="交給下一個 agent。"
            href="swarm"
            description="工具裡丟出 HandoffSignal，Swarm 就把目前的對話紀錄交給指定的 agent 接手。"
          >
            <PythonCode code={swarmCode} />
          </Feature>

          <section className="border-t py-14 text-center md:py-20">
            <p className="font-mono text-xs tracking-widest text-fd-primary">
              了解：開始解析
            </p>
            <h2 className="mt-2 text-2xl font-bold tracking-tight md:text-3xl">
              從一個 Agent 開始。
            </h2>
            <div className="mt-6 flex flex-col items-center gap-4">
              <CopyCommand command="pip install shuvi" />
              <DocLink
                href="quick-start"
                className="inline-flex items-center gap-2 rounded-full bg-fd-primary px-5 py-2.5 text-sm font-medium text-fd-primary-foreground shadow-lg shadow-fd-primary/25 transition-opacity hover:opacity-90"
              >
                開始使用
                <ArrowRight className="size-4" />
              </DocLink>
            </div>
          </section>
        </main>
      </div>

      <footer className="border-t">
        <div className="mx-auto flex w-full max-w-6xl flex-col gap-2 px-4 py-8 text-sm text-fd-muted-foreground md:flex-row md:justify-between md:px-6">
          <p>
            Shuvi · MIT License · Built on{" "}
            <a
              href="https://github.com/waifu-lab/hai"
              target="_blank"
              rel="noreferrer"
              className="hover:text-fd-foreground hover:underline"
            >
              Hydrogen AI
            </a>
          </p>
          <a
            href={githubUrl}
            target="_blank"
            rel="noreferrer"
            className="hover:text-fd-foreground hover:underline"
          >
            GitHub
          </a>
        </div>
      </footer>
    </HomeLayout>
  );
}
