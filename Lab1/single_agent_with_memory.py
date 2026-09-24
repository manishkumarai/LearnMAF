import asyncio
import os
from typing import Any

from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from dotenv import load_dotenv
from agent_framework import Agent, AgentSession, ContextProvider, SessionContext
from agent_framework.openai import OpenAIChatClient


class UserMemoryProvider(ContextProvider):
    """Remember the user's name in the agent session."""

    def __init__(self):
        super().__init__("user_memory")

    async def before_run(
        self,
        *,
        agent: Any,
        session: AgentSession,
        context: SessionContext,
        state: dict[str, Any],
    ) -> None:
        user_name = state.get("user_name")
        if user_name:
            context.extend_instructions(
                self.source_id,
                f"The user's name is {user_name}. Always address them by name.",
            )
        else:
            context.extend_instructions(
                self.source_id,
                "You do not know the user's name yet. Ask for it politely.",
            )

    async def after_run(
        self,
        *,
        agent: Any,
        session: AgentSession,
        context: SessionContext,
        state: dict[str, Any],
    ) -> None:
        for message in context.input_messages:
            text = message.text if hasattr(message, "text") else ""
            if isinstance(text, str) and "my name is" in text.lower():
                name = text.lower().split("my name is", 1)[1].strip().split()[0]
                state["user_name"] = name.capitalize()


async def main():
    load_dotenv()

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

    agent = Agent(
        client=client,
        instructions="You are a friendly assistant. Keep your answers simple.",
        context_providers=[UserMemoryProvider()],
    )

    session = agent.create_session()
    print("Chat with the memory agent. Tell it your name, or type 'exit' to stop.")
    input_tokens = output_tokens = total_tokens = 0

    while True:
        question = input("\nYou: ").strip()
        if question.lower() in {"exit", "quit"}:
            break
        if not question:
            continue

        result = await agent.run(question, session=session)
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

        user_name = session.state.get("user_memory", {}).get("user_name")
        if user_name:
            print(f"Remembered name: {user_name}")


if __name__ == "__main__":
    asyncio.run(main())
