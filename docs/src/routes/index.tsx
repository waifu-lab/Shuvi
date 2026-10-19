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

const heroCode = `import os

from dotenv import load_dotenv
from hai.providers import create_text_provider
from shuvi.agent import Agent
from shuvi.types import AgentConfig, UserMessage

load_dotenv()
llm = create_text_provider(
    "openai",
    model="gpt-4o-mini",
    api_key=os.environ["OPENAI_API_KEY"],
)
schwi = Agent(AgentConfig(
    provider=llm,
    system_prompt="You are Shuvi, an Ex-Machina who wants to understand the human heart.",
))

result = await schwi.run([
    UserMessage(content=[{"type": "text", "text": "What is a heart?"}]),
])
print(result.messages[-1].content)`;

const toolCode = `@tool
def scan(target: str) -> str:
    """Analyze a target and return the result."""
    return f"{target}: analysis complete"


schwi = Agent(AgentConfig(
    provider=llm,
    tools=[scan],
    loop=LoopConfig(max_inner_iterations=10),
))`;

const verifyCode = `def has_answer(messages) -> VerificationRecord:
    text = messages[-1].content or ""
    if "Conclusion" in text:
        return VerificationRecord(passed=True)
    return VerificationRecord(passed=False, reason="End with a conclusion.")


loop = LoopConfig(verify_completion=[has_answer], max_outer_retries=3)`;

const swarmCode = `@tool
def to_riku(reason: str) -> str:
    """Hand the conversation to the strategist."""
    raise HandoffSignal("riku", context=reason)


swarm = Swarm({"schwi": schwi, "riku": riku})
result = await swarm.run("schwi", messages)`;

const callbacks = [
  { name: "on_chunk", desc: "Each streamed chunk" },
  { name: "tool_call", desc: "A tool is about to run" },
  { name: "tool_result", desc: "What the tool returned" },
  { name: "on_tool_error", desc: "A tool raised an error" },
  { name: "state_update", desc: "Loop state changed" },
  { name: "iteration_end", desc: "All tools in a round finished" },
];

function CopyCommand({ command }: { command: string }) {
  const [copied, setCopied] = useState(false);

  async function copy() {
    try {
      await navigator.clipboard.writeText(command);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {}
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
          Read the docs
          <ArrowRight className="size-4" />
        </DocLink>
      </div>
      <div className="mt-8 min-w-0">{children}</div>
    </section>
  );
}

function Home() {
  return (
    <HomeLayout {...baseOptions()} links={[{ text: "Docs", url: "/docs" }]}>
      <div className="relative">
        <div className="circuit-grid pointer-events-none absolute inset-x-0 top-0 h-[640px]" />
        <main className="relative mx-auto w-full max-w-6xl px-4 md:px-6">
          <section className="grid grid-cols-1 items-center gap-10 py-14 md:py-20 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)]">
            <div>
              <h1 className="mt-5 text-5xl font-extrabold tracking-tight md:text-6xl">
                Shuvi
                <span className="ml-3 align-middle text-2xl font-bold text-fd-primary md:text-3xl">
                  シュヴィ
                </span>
              </h1>
              <p className="mt-4 max-w-lg text-lg text-fd-muted-foreground">
                A lightweight async agent loop
              </p>
              <div className="mt-8 flex flex-wrap gap-3">
                <DocLink
                  href="quick-start"
                  className="inline-flex items-center gap-2 rounded-full bg-fd-primary px-5 py-2.5 text-sm font-medium text-fd-primary-foreground shadow-lg shadow-fd-primary/25 transition-opacity hover:opacity-90"
                >
                  Get started
                  <ArrowRight className="size-4" />
                </DocLink>
              </div>
              <div className="mt-6">
                <CopyCommand command="pip install shuvi" />
              </div>
            </div>
            <SchwiCore className="mx-auto w-full max-w-75 sm:max-w-100 lg:max-w-130" />
          </section>

          <Feature
            index="01 · Start"
            title="Up and running in a few lines"
            href="quick-start"
            description="Give it a model and a system prompt, then call run()."
          >
            <PythonCode code={heroCode} />
          </Feature>

          <Feature
            index="02 · Tools"
            title="Build tools"
            href="tools"
            description="Turn any function into a tool with @tool."
          >
            <PythonCode code={toolCode} />
          </Feature>

          <Feature
            index="03 · Callbacks"
            title="Event handling"
            href="callbacks"
            description="Hook into every step of the loop."
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
            index="04 · Multi-agent"
            title="Multi Agent System"
            href="swarm"
            description="Hand a conversation from one agent to another."
          >
            <PythonCode code={swarmCode} />
          </Feature>

          <section className="border-t py-14 text-center md:py-20">
            <h2 className="text-2xl font-bold tracking-tight md:text-3xl">
              Try it now
            </h2>
            <div className="mt-6 flex flex-col items-center gap-4">
              <CopyCommand command="pip install shuvi" />
              <DocLink
                href="quick-start"
                className="inline-flex items-center gap-2 rounded-full bg-fd-primary px-5 py-2.5 text-sm font-medium text-fd-primary-foreground shadow-lg shadow-fd-primary/25 transition-opacity hover:opacity-90"
              >
                Get started
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
