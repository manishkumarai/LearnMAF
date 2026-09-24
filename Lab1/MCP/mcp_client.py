import asyncio
import os

from agent_framework import (
    Agent,
    FunctionInvocationContext,
    FunctionMiddleware,
    MCPStreamableHTTPTool,
)
from agent_framework.openai import OpenAIChatClient
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from dotenv import load_dotenv


class ToolObservabilityMiddleware(FunctionMiddleware):
    """Print the name, input, and output of every tool call."""

    def __init__(self, server_name: str, server_url: str):
        self.server_name = server_name
        self.server_url = server_url

    async def process(self, context: FunctionInvocationContext, call_next) -> None:
        print(f"\n[MCP server] {self.server_name}", flush=True)
        print(f"[MCP server URL] {self.server_url}", flush=True)
        print(f"\n[Tool called] {context.function.name}", flush=True)
        print(f"[Tool input] {context.arguments}", flush=True)

        await call_next()

        print(f"[Tool output] {context.result}", flush=True)
        print("[Agent] Waiting for the final response...", flush=True)


async def main():
    load_dotenv()

    server_url = input(
        "Enter the MCP server URL "
        "(default: http://127.0.0.1:8000/mcp): "
    ).strip()
    server_url = server_url or "http://127.0.0.1:8000/mcp"

    key_vault = SecretClient(
        vault_url="https://kv-mkbhopal919174214256.vault.azure.net/",
        credential=DefaultAzureCredential(),
    )
    api_key = key_vault.get_secret("AZURE-OPENAI-API-KEY").value

    client = OpenAIChatClient(
        api_key=api_key,
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        model=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
    )

    async with MCPStreamableHTTPTool(
        name="learnmaf_server",
        url=server_url,
        approval_mode="never_require",
        request_timeout=30,
    ) as mcp_tools:
        print(f"\nConnected to MCP server: learnmaf_server")
        print(f"MCP server URL: {server_url}")

        agent = Agent(
            client=client,
            instructions=(
                "You are a helpful assistant. Use the MCP tools for weather "
                "and current date/time questions."
            ),
            tools=mcp_tools,
            middleware=[
                ToolObservabilityMiddleware("learnmaf_server", server_url)
            ],
        )

        session = agent.create_session()
        print("Connected to MCP server. Type 'exit' to stop.")
        input_tokens = output_tokens = total_tokens = 0

        while True:
            question = input("\nYou: ").strip()
            if question.lower() in {"exit", "quit"}:
                break
            if not question:
                continue

            print("[Agent] Thinking and calling tools if needed...", flush=True)
            try:
                result = await asyncio.wait_for(
                    agent.run(question, session=session),
                    timeout=120,
                )
            except asyncio.TimeoutError as error:
                raise TimeoutError(
                    "The agent did not finish within 120 seconds. "
                    "Check the Azure OpenAI endpoint, deployment, and MCP server."
                ) from error
            print(f"Agent: {result}")

            usage = result.usage_details or {}
            input_tokens += usage.get("input_token_count", 0)
            output_tokens += usage.get("output_token_count", 0)
            total_tokens += usage.get("total_token_count", 0)
            print(
                "Cumulative tokens: "
                f"input={input_tokens}, "
                f"output={output_tokens}, "
                f"total={total_tokens}"
            )


if __name__ == "__main__":
    asyncio.run(main())
