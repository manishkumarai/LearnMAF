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

Copy `.env.example` to `.env` in the project root and set:

- `AZURE_OPENAI_ENDPOINT`: your Azure OpenAI resource endpoint
- `AZURE_OPENAI_DEPLOYMENT`: the deployment name in Azure (not necessarily the model name)

The API key is read from Key Vault at runtime, so it is not stored in `.env`.
The client uses the Agent Framework Responses API default version.

## 4. Run the examples

The examples are in the `Lab1` and `Lab2` folders. Examples that call Azure
OpenAI use the root `.env` file and Key Vault configuration above.

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

### Harness research assistant

Lab2 introduces `create_harness_agent`, which combines an agent with planning
and execution modes, todo tracking, context compaction, file memory, telemetry,
web search, and an autonomous work loop.

Run the research assistant from the project root:

```bash
python Lab2/harness_research.py
```

Start by entering a research topic. The agent begins in `plan` mode and creates
a plan for review. When the plan is satisfactory, ask the agent to execute it.
In `execute` mode, the harness continues through the open todos automatically,
up to the configured limit of 10 passes.

After each research question, the program asks whether to show the full
observability log. Choose `y` to display the exposed operational details while
the agent works, or `n` to display only its streamed response:

```text
Show full observability log? (y/n):
```

- Startup, configuration, authentication, and readiness stages.
- Live streamed agent responses and non-text events such as web searches.
- Model request and response counts, latency, model name, response ID, and
  finish reason.
- Harness tool names, inputs, outputs, failures, and execution time.
- Todo-loop pass numbers, continuation decisions, and next-pass messages.
- Per-model-call, per-turn, and cumulative session token usage, including
  input, output, reasoning, cache-created, and cache-read tokens when reported
  by the model provider.
- Per-turn and total program execution time.

The console reports observable stages and tool activity, but it does not expose
the model's private chain-of-thought. Final research reports are saved through
the harness file-memory provider. By default, its data is stored under
`agent-file-memory` in the directory from which the script is launched.

### Multi-agent motor FNOL harness

Run the simulated motor insurance First Notice of Loss (FNOL) workflow:

```bash
python Lab2/harness_motor_claim.py
```

The lead `FNOLCoordinator` gathers claim details, prepares a plan, and delegates
work to five background specialists:

- `FNOLIntakeSpecialist` validates completeness and normalizes the loss facts.
- `CoverageReviewSpecialist` identifies policy and coverage questions for a
  human adjuster.
- `DamageTriageSpecialist` reviews safety, drivability, towing, and inspection
  needs.
- `FraudSignalSpecialist` identifies neutral inconsistencies and verification
  needs without making accusations.
- `ClaimsRoutingSpecialist` recommends priority, ownership, and next actions for
  human claims handling.

The coordinator can start independent assessments concurrently, wait for all
specialists, retrieve their results, and synthesize a draft FNOL report. It uses
the same optional full-observability console as the research harness, with each
model and tool event labeled by agent name.

This is an educational simulation. It does not connect to an insurer or submit
a real claim. It must not automatically approve or deny coverage, determine
liability or fraud, authorize repairs, or promise payment. Its output requires
verification by an authorized human claims professional.

Both harness examples set `store=False`, so conversation and tool-call history
is replayed from the local `InMemoryHistoryProvider`. This avoids depending on
Azure retaining a `previous_response_id` between model calls. After changing
this setting, restart the Python process so it creates a fresh session without
an old service-side response ID.

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
- `create_harness_agent` assembles planning, todos, memory, compaction, web
  search, telemetry, and looping around an agent.
- `ChatMiddleware` observes each underlying model request and response.
- Streaming with `agent.run(..., stream=True)` exposes response updates while
  the agent is working.
- `todos_remaining(...)` controls whether the harness starts another autonomous
  execution pass.
- `background_agents` lets a coordinator launch specialist tasks concurrently,
  wait for completion, retrieve results, and continue or clear those tasks.

References:

- [Microsoft Agent Framework: Your first agent](https://learn.microsoft.com/agent-framework/get-started/your-first-agent)
- [Agent Framework on PyPI](https://pypi.org/project/agent-framework/)
