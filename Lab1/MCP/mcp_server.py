from datetime import datetime
from random import randint
from typing import Annotated

from mcp.server.fastmcp import FastMCP
from pydantic import Field


mcp = FastMCP(
    "LearnMAF Tools",
    instructions="Tools for weather and current date/time questions.",
)


@mcp.tool()
def get_weather(
    location: Annotated[
        str, Field(description="The location to get the weather for.")
    ],
) -> str:
    """Get simulated weather for a location."""
    conditions = ["sunny", "cloudy", "rainy", "stormy"]
    return (
        f"The weather in {location} is {conditions[randint(0, 3)]} "
        f"with a high of {randint(10, 30)} degrees Celsius."
    )


@mcp.tool()
def get_current_datetime() -> str:
    """Get the current local date and time."""
    return datetime.now().astimezone().isoformat(timespec="seconds")


if __name__ == "__main__":
    print("MCP server running at http://127.0.0.1:8000/mcp")
    mcp.run(transport="streamable-http")
