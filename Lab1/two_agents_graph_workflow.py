import asyncio
from enum import Enum

from agent_framework import Executor, WorkflowBuilder, WorkflowContext, executor, handler
from typing_extensions import Never


class WorkflowStep(str, Enum):
    """States used by the two-step workflow."""

    RECEIVED = "received"
    UPPERCASED = "uppercased"
    REVERSED = "reversed"


class UpperCase(Executor):
    """Convert incoming text to uppercase."""

    def __init__(self, id: str):
        super().__init__(id=id)

    @handler
    async def to_upper_case(self, text: str, ctx: WorkflowContext[str]) -> None:
        print(f"\nStep 1 - State: {WorkflowStep.RECEIVED.value}")
        print(f"Input: {text}")
        upper_text = text.upper()
        print(f"Step 1 - State: {WorkflowStep.UPPERCASED.value}")
        print(f"Output: {upper_text}")
        await ctx.send_message(upper_text)


@executor(id="reverse_text")
async def reverse_text(text: str, ctx: WorkflowContext[Never, str]) -> None:
    """Reverse the text and emit it as the workflow output."""
    print(f"\nStep 2 - State: {WorkflowStep.UPPERCASED.value}")
    print(f"Input: {text}")
    reversed_text = text[::-1]
    print(f"Step 2 - State: {WorkflowStep.REVERSED.value}")
    print(f"Output: {reversed_text}")
    await ctx.yield_output(reversed_text)


def create_workflow():
    """Build the workflow: UpperCase -> reverse_text."""
    upper_case = UpperCase(id="upper_case")
    return WorkflowBuilder(start_executor=upper_case).add_edge(
        upper_case, reverse_text
    ).build()


async def main():
    text = input("Enter text to uppercase and reverse: ").strip()
    if not text:
        print("Please enter some text.")
        return

    workflow = create_workflow()
    events = await workflow.run(text)

    print(f"Workflow output: {events.get_outputs()}")
    print(f"Final state: {events.get_final_state()}")
    print(
        "\nGraph diagram:\n"
        "  Input text\n"
        "      |\n"
        "      v\n"
        "[upper_case]\n"
        "  UpperCase\n"
        "      |\n"
        "      v\n"
        "[reverse_text]\n"
        "  Reverse\n"
        "      |\n"
        "      v\n"
        "  Final output"
    )


if __name__ == "__main__":
    asyncio.run(main())
