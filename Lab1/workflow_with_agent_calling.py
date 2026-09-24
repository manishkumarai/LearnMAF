import asyncio
import os
import warnings

from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from dotenv import load_dotenv
from agent_framework import Agent, workflow
from agent_framework.openai import OpenAIChatClient

# The workflow API is experimental in the current Agent Framework release.
warnings.filterwarnings(
    "ignore",
    message=r"\[FUNCTIONAL_WORKFLOWS\].*",
    category=FutureWarning,
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

    writer = Agent(
        client=client,
        instructions="Write a short poem with no more than four lines.",
    )
    reviewer = Agent(
        client=client,
        instructions="Review the poem in one short sentence.",
    )

    @workflow
    async def poem_workflow(topic: str) -> str:
        """Write a poem and then review it with two agents."""
        input_tokens = output_tokens = total_tokens = 0

        poem_result = await writer.run(f"Write a poem about: {topic}")
        poem = poem_result.text
        usage = poem_result.usage_details or {}
        input_tokens += usage.get("input_token_count", 0)
        output_tokens += usage.get("output_token_count", 0)
        total_tokens += usage.get("total_token_count", 0)

        review_result = await reviewer.run(f"Review this poem:\n{poem}")
        review = review_result.text
        usage = review_result.usage_details or {}
        input_tokens += usage.get("input_token_count", 0)
        output_tokens += usage.get("output_token_count", 0)
        total_tokens += usage.get("total_token_count", 0)

        print(
            "Cumulative tokens: "
            f"input={input_tokens}, "
            f"output={output_tokens}, "
            f"total={total_tokens}"
        )
        return f"Poem:\n{poem}\n\nReview: {review}"

    workflow_instance = poem_workflow.build()
    result = await workflow_instance.run("a cat learning to code")
    print(result.get_outputs()[0])


if __name__ == "__main__":
    asyncio.run(main())
