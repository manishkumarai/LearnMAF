# Learn Microsoft Agent Framework

A small beginner tutorial for creating an agent with Microsoft Agent Framework,
Azure OpenAI, and Azure Key Vault.

## 1. Install the dependencies

Python 3.10 or newer is required.

```bash
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
python -m pip install -r requirements.txt
```

## 2. Store the API key in Azure Key Vault

This tutorial uses the Key Vault named `kv-mkbhopal919174214256`.

Sign in locally and create the secret:

```bash
az login
az keyvault secret set \
  --vault-name kv-mkbhopal919174214256 \
  --name AZURE-OPENAI-API-KEY \
  --value "your-azure-openai-api-key"
```

Your signed-in Azure account needs permission to read secrets from the vault.
For an RBAC-enabled vault, assign the **Key Vault Secrets User** role.

The Python program uses `DefaultAzureCredential`, which uses your local Azure
CLI login.

## 3. Configure Azure OpenAI

Copy `.env.example` to `.env` and set:

- `AZURE_OPENAI_ENDPOINT`: your Azure OpenAI resource endpoint
- `AZURE_OPENAI_DEPLOYMENT`: the deployment name in Azure (not necessarily the model name)

The API key is read from Key Vault at runtime, so it is not stored in `.env`.
The client uses the Agent Framework Responses API default version.

## 4. Run the examples

The examples are in the `Lab1` folder. Examples that call Azure OpenAI use the
Key Vault configuration above.

### Single agent

Run the basic interactive Python tutor:

```bash
python Lab1/single_agent.py
```

### Single agent with a tool

Run the weather agent, which demonstrates a function tool:

```bash
python Lab1/single_agent_with_tools.py
```

Ask about the weather in a location. The agent can call `get_weather`.

### Two agents

Run two comedian agents that tell jokes to each other:

```bash
python Lab1/two_agents_multi_turn.py
```

The conversation stops when an agent says `bye` or after 10 turns.

Each agent has its own `AgentSession`, and cumulative token usage is displayed
after every turn.

### Workflow with agent calling

Run a functional workflow where one agent writes a poem and another agent
reviews it:

```bash
python Lab1/workflow_with_agent_calling.py
```

Enter a poem topic when prompted. The program shows each workflow step,
intermediate state, poem, review, token usage, and final workflow state.
The functional workflow API is experimental in the current Agent Framework
release.

### First Graph Workflow — Chain executors with edges

This example introduces the graph API. Graph workflows give you control over
execution topology, including edges, fan-out/fan-in, switch/case routing, and
superstep-based checkpointing.

The sample builds a minimal graph with two steps:

1. Convert text to uppercase using a class-based executor.
2. Reverse the text using a function-based executor.

No external services are required for this example:

```bash
python Lab1/two_agents_graph_workflow.py
```

Enter text when prompted. The program shows each state transition and prints
the workflow graph diagram after the final output.

### Agent with memory

Run the memory example:

```bash
python Lab1/single_agent_with_memory.py
```

Tell the agent your name. A `UserMemoryProvider` stores it in the session and
personalizes later responses. This example also demonstrates state management:
the provider stores the name in its provider-scoped state under
`session.state["user_memory"]["user_name"]`. The state is reused on every
turn, so the agent remembers the name during the session.

### MCP server

Start the MCP server first:

```bash
python Lab1/MCP/mcp_server.py
```

The server uses Streamable HTTP and listens at:

```text
http://127.0.0.1:8000/mcp
```

It exposes these tools:

- `get_weather(location)`: returns simulated weather.
- `get_current_datetime()`: returns the current local date and time.

The MCP server does not call Azure OpenAI and does not require the Key Vault
configuration.

### MCP client

In a second terminal, start the interactive client:

```bash
python Lab1/MCP/mcp_client.py
```

Enter the MCP server URL when prompted, or press Enter to use the default.
Then ask questions such as:

```text
What is the weather in Seattle?
What is the current date and time?
```

The client connects the MCP tools to an Agent Framework agent. For every tool
call it logs the MCP server name, server URL, tool name, tool input, and tool
output. It also prints cumulative input, output, and total token counts.

The client uses a 30-second MCP request timeout and a 120-second timeout for
the complete agent response. Keep the MCP server running while using the
client. Type `exit` or `quit` to stop the client, and use Ctrl+C to stop the
server.

For the interactive examples, type questions in the terminal and enter
`exit` or `quit` to stop.

All interactive examples print cumulative input, output, and total token
counts from `AgentResponse.usage_details`.

## What to learn

- `SecretClient` reads the API key from Azure Key Vault.
- `OpenAIChatClient` connects Agent Framework to Azure OpenAI.
- `Agent` adds instructions and agent behavior around the client.
- `agent.create_session()` keeps the conversation history.
- `agent.run(...)` sends a user message and waits for the complete response.
- `result.usage_details` exposes token usage for observability.
- `@tool` lets an agent call a Python function.
- `ContextProvider` adds dynamic context and stores information in session state.
- `before_run` reads state and injects personalized instructions before a call.
- `after_run` updates state after a call by extracting the user's name.
- `session.state` provides state management for the current agent session.
- `@workflow` chains asynchronous agent calls into a functional workflow.
- `WorkflowBuilder` connects executors into a graph with explicit edges.
- `WorkflowContext` sends messages between graph steps and yields outputs.
- Graph edges define execution topology and control how data moves between
  executors.
- `MCPStreamableHTTPTool` connects an Agent Framework agent to remote MCP tools.
- `FunctionMiddleware` observes tool calls without changing their behavior.

References:

- [Microsoft Agent Framework: Your first agent](https://learn.microsoft.com/agent-framework/get-started/your-first-agent)
- [Agent Framework on PyPI](https://pypi.org/project/agent-framework/)
