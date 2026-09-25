"""Interactive research assistant built with Agent Framework's agent harness.

The harness adds planning/execution modes, todo tracking, conversation-history
persistence, context compaction, file memory, telemetry, and web search to the
same Azure OpenAI setup used by ``Lab1/single_agent.py``.
"""

import asyncio
import inspect
import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from agent_framework import (
    AgentModeProvider,
    ChatContext,
    ChatMiddleware,
    FunctionInvocationContext,
    FunctionMiddleware,
    ResponseStream,
    create_harness_agent,
    todos_remaining,
    todos_remaining_message,
)
from agent_framework.openai import OpenAIChatClient
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from dotenv import load_dotenv


RESEARCH_INSTRUCTIONS = """\
## Research Assistant Instructions

You are a research assistant. When given a research topic, research it
thoroughly using web search. Use your knowledge to form good search queries and
hypotheses, but verify claims with the available tools rather than relying on
memory alone.

### Research quality

- Consult multiple sources and cross-reference important claims.
- If sources disagree, explain the discrepancy and which source is more
  reliable.
- If a search is unsuccessful, try alternative queries before giving up.
- Keep track of sources for the final response.

### Presenting results

- Use clear Markdown headings.
- Cite sources inline with links.
- End with a short list of key takeaways.
- Save the final report to file memory so it remains available after context
  compaction.
"""

TOKEN_FIELDS = (
    "input_token_count",
    "output_token_count",
    "total_token_count",
    "reasoning_output_token_count",
    "cache_creation_input_token_count",
    "cache_read_input_token_count",
)


def display_value(value: Any) -> str:
    """Format observable tool data without requiring it to be JSON serializable."""
    try:
        return json.dumps(value, indent=2, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        return str(value)


class ConsoleObservability:
    """Collect and print live observability for model, tool, and loop stages."""

    def __init__(self) -> None:
        self.program_started = time.perf_counter()
        self.turn_started = self.program_started
        self.turn_number = 0
        self.model_calls = 0
        self.tool_calls = 0
        self.loop_iterations = 0
        self.turn_usage = self.empty_usage()
        self.session_usage = self.empty_usage()
        self.stream_role: str | None = None
        self.seen_stream_events: set[str] = set()
        self.full_observability = True

    @staticmethod
    def empty_usage() -> dict[str, int]:
        return {field: 0 for field in TOKEN_FIELDS}

    def event(self, category: str, message: str, *, force: bool = False) -> None:
        if not self.full_observability and not force:
            return
        self.stream_role = None
        clock = datetime.now().astimezone().strftime("%H:%M:%S")
        elapsed = time.perf_counter() - self.program_started
        print(f"\n[{clock} | +{elapsed:8.2f}s] [{category}] {message}", flush=True)

    def stream_text(self, role: str | None, text: str) -> None:
        if not text:
            return
        normalized_role = role or "assistant"
        if normalized_role != self.stream_role:
            print(f"\n[{normalized_role.capitalize()}] ", end="", flush=True)
            self.stream_role = normalized_role
        print(text, end="", flush=True)

    def stream_update(self, update: Any) -> None:
        """Print text deltas and non-text events such as hosted web-search calls."""
        self.stream_text(str(update.role) if update.role else None, update.text)
        if not self.full_observability:
            return
        for content in update.contents or []:
            content_type = getattr(content, "type", "unknown")
            if content_type == "text":
                continue
            payload = content.to_dict() if hasattr(content, "to_dict") else content
            rendered = display_value(payload)
            signature = f"{content_type}:{rendered}"
            if signature in self.seen_stream_events:
                continue
            self.seen_stream_events.add(signature)
            self.event("STREAM EVENT", f"type={content_type}")
            print(f"  Data:\n{rendered}", flush=True)

    def start_turn(self, question: str, *, full_observability: bool) -> None:
        self.full_observability = full_observability
        self.stream_role = None
        self.turn_number += 1
        self.turn_started = time.perf_counter()
        self.model_calls = 0
        self.tool_calls = 0
        self.loop_iterations = 0
        self.turn_usage = self.empty_usage()
        self.seen_stream_events.clear()
        self.event(
            "TURN",
            f"Starting turn {self.turn_number}; user input characters={len(question)}",
        )

    def add_usage(self, usage: Any) -> None:
        if not usage:
            return
        for field in TOKEN_FIELDS:
            value = usage.get(field, 0) or 0
            self.turn_usage[field] += value
            self.session_usage[field] += value

    @staticmethod
    def usage_line(usage: dict[str, int]) -> str:
        return (
            f"input={usage['input_token_count']:,}, "
            f"output={usage['output_token_count']:,}, "
            f"total={usage['total_token_count']:,}, "
            f"reasoning={usage['reasoning_output_token_count']:,}, "
            f"cache-created={usage['cache_creation_input_token_count']:,}, "
            f"cache-read={usage['cache_read_input_token_count']:,}"
        )

    def finish_turn(self, result: Any) -> None:
        if not self.full_observability:
            return
        elapsed = time.perf_counter() - self.turn_started
        finish_reason = getattr(result, "finish_reason", None) or "not reported"
        response_id = getattr(result, "response_id", None) or "not reported"
        self.event(
            "TURN SUMMARY",
            (
                f"turn={self.turn_number}, elapsed={elapsed:.2f}s, "
                f"model calls={self.model_calls}, tool calls={self.tool_calls}, "
                f"loop passes={self.loop_iterations}, finish={finish_reason}, "
                f"response_id={response_id}"
            ),
        )
        print(f"  Turn tokens:    {self.usage_line(self.turn_usage)}")
        print(f"  Session tokens: {self.usage_line(self.session_usage)}", flush=True)


class ModelObservabilityMiddleware(ChatMiddleware):
    """Report every request to and response from the underlying model."""

    def __init__(
        self,
        observer: ConsoleObservability,
        agent_label: str = "agent",
    ) -> None:
        self.observer = observer
        self.agent_label = agent_label

    async def process(self, context: ChatContext, call_next) -> None:
        self.observer.model_calls += 1
        call_number = self.observer.model_calls
        started = time.perf_counter()
        roles = [str(message.role) for message in context.messages]
        options = context.options or {}
        tools = options.get("tools") or []
        self.observer.event(
            "MODEL REQUEST",
            (
                f"agent={self.agent_label}, call={call_number}, "
                f"messages={len(context.messages)}, "
                f"roles={roles}, tools={len(tools)}, stream={context.stream}"
            ),
        )

        try:
            await call_next()
        except Exception as error:
            elapsed = time.perf_counter() - started
            self.observer.event(
                "MODEL ERROR",
                (
                    f"agent={self.agent_label}, call={call_number}, "
                    f"elapsed={elapsed:.2f}s, error={error!r}"
                ),
            )
            raise

        async def report_response(response: Any) -> Any:
            elapsed = time.perf_counter() - started
            usage = getattr(response, "usage_details", None) or {}
            self.observer.add_usage(usage)
            self.observer.event(
                "MODEL RESPONSE",
                (
                    f"agent={self.agent_label}, call={call_number}, "
                    f"elapsed={elapsed:.2f}s, "
                    f"model={getattr(response, 'model', None) or 'not reported'}, "
                    f"finish={getattr(response, 'finish_reason', None) or 'not reported'}, "
                    f"response_id={getattr(response, 'response_id', None) or 'not reported'}"
                ),
            )
            response_usage = {
                field: usage.get(field, 0) or 0 for field in TOKEN_FIELDS
            }
            if self.observer.full_observability:
                print(f"  Tokens: {self.observer.usage_line(response_usage)}")
            return response

        if context.stream and isinstance(context.result, ResponseStream):
            context.result.with_result_hook(report_response)
        elif context.result is not None:
            await report_response(context.result)


class ToolObservabilityMiddleware(FunctionMiddleware):
    """Report every local harness tool invocation, including input and output."""

    def __init__(
        self,
        observer: ConsoleObservability,
        agent_label: str = "agent",
    ) -> None:
        self.observer = observer
        self.agent_label = agent_label

    async def process(self, context: FunctionInvocationContext, call_next) -> None:
        self.observer.tool_calls += 1
        call_number = self.observer.tool_calls
        started = time.perf_counter()
        self.observer.event(
            "TOOL START",
            (
                f"agent={self.agent_label}, call={call_number}, "
                f"name={context.function.name}"
            ),
        )
        if self.observer.full_observability:
            print(f"  Input:\n{display_value(context.arguments)}", flush=True)

        try:
            await call_next()
        except Exception as error:
            elapsed = time.perf_counter() - started
            self.observer.event(
                "TOOL ERROR",
                (
                    f"agent={self.agent_label}, call={call_number}, "
                    f"name={context.function.name}, "
                    f"elapsed={elapsed:.2f}s, error={error!r}"
                ),
            )
            raise

        elapsed = time.perf_counter() - started
        self.observer.event(
            "TOOL END",
            (
                f"agent={self.agent_label}, call={call_number}, "
                f"name={context.function.name}, elapsed={elapsed:.2f}s"
            ),
        )
        if self.observer.full_observability:
            print(f"  Output:\n{display_value(context.result)}", flush=True)


def load_environment() -> list[Path]:
    """Load configuration from Lab2 or the project root."""
    project_root = Path(__file__).resolve().parent.parent
    env_files = (
        Path(__file__).with_name(".env"),
        project_root / ".env",
    )

    loaded_files = []
    for env_file in env_files:
        if env_file.is_file():
            load_dotenv(env_file, override=False)
            loaded_files.append(env_file)
    return loaded_files


def required_environment_variable(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(
            f"Missing {name}. Add it to Lab2/.env, the project .env, "
            "or export it in your shell."
        )
    return value


def ask_for_full_observability() -> bool:
    """Ask whether detailed operational events should be printed this turn."""
    while True:
        answer = input("Show full observability log? (y/n): ").strip().lower()
        if answer in {"y", "yes"}:
            return True
        if answer in {"n", "no"}:
            return False
        print("Please enter 'y' or 'n'.")


async def main() -> None:
    observer = ConsoleObservability()
    observer.event("STARTUP", "Loading environment configuration")
    loaded_files = load_environment()
    observer.event(
        "CONFIG",
        "Loaded: " + ", ".join(str(path) for path in loaded_files),
    )

    azure_endpoint = required_environment_variable("AZURE_OPENAI_ENDPOINT")
    deployment_name = required_environment_variable("AZURE_OPENAI_DEPLOYMENT")
    observer.event(
        "CONFIG",
        f"Azure endpoint={azure_endpoint}; deployment={deployment_name}",
    )

    credential_started = time.perf_counter()
    observer.event("AUTH", "Reading AZURE-OPENAI-API-KEY from Azure Key Vault")
    key_vault = SecretClient(
        vault_url="https://kv-mkbhopal919174214256.vault.azure.net/",
        credential=DefaultAzureCredential(),
    )
    api_key = key_vault.get_secret("AZURE-OPENAI-API-KEY").value
    observer.event(
        "AUTH",
        f"Key Vault secret retrieved in {time.perf_counter() - credential_started:.2f}s",
    )

    observer.event("STARTUP", "Creating Azure OpenAI chat client")
    client = OpenAIChatClient(
        api_key=api_key,
        azure_endpoint=azure_endpoint,
        model=deployment_name,
        middleware=[
            ModelObservabilityMiddleware(observer, "ResearchAgent"),
            ToolObservabilityMiddleware(observer, "ResearchAgent"),
        ],
    )

    base_should_continue = todos_remaining(looping_modes=["execute"])

    async def observed_should_continue(**kwargs) -> Any:
        result = base_should_continue(**kwargs)
        if inspect.isawaitable(result):
            result = await result
        iteration = kwargs.get("iteration", 0)
        observer.loop_iterations = max(observer.loop_iterations, iteration)
        decision = result[0] if isinstance(result, tuple) else result
        feedback = result[1] if isinstance(result, tuple) and len(result) > 1 else None
        observer.event(
            "LOOP DECISION",
            (
                f"pass={iteration}, todos remain={bool(decision)}, "
                f"action={'continue automatically' if decision else 'return to user'}, "
                f"feedback={feedback or 'none'}"
            ),
        )
        return result

    async def observed_next_message(**kwargs) -> Any:
        message = todos_remaining_message(**kwargs)
        if inspect.isawaitable(message):
            message = await message
        observer.event(
            "LOOP INPUT",
            f"Starting the next autonomous pass with: {message or 'previous input'}",
        )
        return message

    observer.event("STARTUP", "Building research harness and observability pipeline")
    agent = create_harness_agent(
        client=client,
        name="ResearchAgent",
        description="A research assistant that plans and executes research tasks.",
        agent_instructions=RESEARCH_INSTRUCTIONS,
        mode_provider=AgentModeProvider(default_mode="plan"),
        max_context_window_tokens=128_000,
        max_output_tokens=16_384,
        loop_should_continue=observed_should_continue,
        loop_next_message=observed_next_message,
        loop_max_iterations=10,
        # Keep history locally instead of relying on Azure to retain response IDs.
        default_options={"store": False},
    )

    session = agent.create_session()
    observer.event(
        "READY",
        f"Agent={agent.name}; session_id={session.session_id}; initial mode=plan",
    )
    print("Research assistant ready in plan mode. Type 'exit' to stop.")
    print("Describe a topic, then approve the plan by asking it to execute.")
    print(
        "Observability includes operational stages and tool activity; "
        "private model chain-of-thought is not exposed."
    )

    while True:
        try:
            question = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if question.lower() in {"exit", "quit"}:
            break
        if not question:
            continue

        try:
            full_observability = ask_for_full_observability()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        observer.start_turn(
            question,
            full_observability=full_observability,
        )
        try:
            # A previous failed run may have left a stale Azure response ID.
            session.service_session_id = None
            response_stream = agent.run(question, stream=True, session=session)
            async for update in response_stream:
                observer.stream_update(update)
            result = await response_stream.get_final_response()
        except Exception as error:
            elapsed = time.perf_counter() - observer.turn_started
            observer.event(
                "TURN ERROR",
                f"turn={observer.turn_number}, elapsed={elapsed:.2f}s, error={error!r}",
                force=True,
            )
            continue

        observer.finish_turn(result)

    if observer.full_observability:
        observer.event(
            "SHUTDOWN",
            (
                f"Completed {observer.turn_number} turn(s) in "
                f"{time.perf_counter() - observer.program_started:.2f}s; "
                f"session tokens: {observer.usage_line(observer.session_usage)}"
            ),
        )
    else:
        print("\nResearch assistant stopped.")


if __name__ == "__main__":
    asyncio.run(main())
