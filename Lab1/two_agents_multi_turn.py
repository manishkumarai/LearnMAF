import asyncio
import os

from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from dotenv import load_dotenv
from agent_framework import Agent
from agent_framework.openai import OpenAIChatClient


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

    agent_one = Agent(
        client=client,
        instructions=(
            "You are a comedian named Agent One. Tell short, family-friendly "
            "jokes. After hearing the other agent's joke, tell a related joke. "
            "Say 'bye' when you want to end the conversation."
        ),
    )
    agent_two = Agent(
        client=client,
        instructions=(
            "You are a comedian named Agent Two. Tell short, family-friendly "
            "jokes. After hearing the other agent's joke, tell a related joke. "
            "Say 'bye' when you want to end the conversation."
        ),
    )

    # Each agent has its own session, so each one remembers its previous turns.
    session_one = agent_one.create_session()
    session_two = agent_two.create_session()
    message = "Tell Agent Two your first joke."
    input_tokens = output_tokens = total_tokens = 0

    for turn in range(1, 11):
        agent = agent_one if turn % 2 else agent_two
        session = session_one if turn % 2 else session_two
        # Reusing the session maintains multi-turn conversation history.
        result = await agent.run(message, session=session)
        response = result.text

        print(
            f"\nTurn {turn} - "
            f"{'Agent One' if turn % 2 else 'Agent Two'}: {response}"
        )
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

        if "bye" in response.lower():
            print("\nThe agents said goodbye.")
            break

        # Pass the current response to the other agent for the next turn.
        message = f"The other agent said: {response}\nReply with a related joke."
    else:
        print("\nThe conversation stopped after 10 turns.")


if __name__ == "__main__":
    asyncio.run(main())
