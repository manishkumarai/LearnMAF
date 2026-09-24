import asyncio
import os
from random import randint
from typing import Annotated

from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from dotenv import load_dotenv
from agent_framework import Agent, tool
from agent_framework.openai import OpenAIChatClient
from pydantic import Field


@tool(approval_mode="never_require")
def get_weather(
    location: Annotated[
        str, Field(description="The location to get the weather for.")
    ],
) -> str:
    """Get the weather for a given location."""
    conditions = ["sunny", "cloudy", "rainy", "stormy"]
    return (
        f"The weather in {location} is {conditions[randint(0, 3)]} "
        f"with a high of {randint(10, 30)} degrees Celsius."
    )


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
        instructions=(
            "You are a helpful weather agent. Use the get_weather tool "
            "to answer weather questions."
        ),
        tools=[get_weather],
    )

    session = agent.create_session()
    print("Chat with the weather agent. Type 'exit' to stop.")
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


if __name__ == "__main__":
    asyncio.run(main())
