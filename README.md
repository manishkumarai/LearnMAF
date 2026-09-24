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

The examples are in the `Lab1` folder.

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

References:

- [Microsoft Agent Framework: Your first agent](https://learn.microsoft.com/agent-framework/get-started/your-first-agent)
- [Agent Framework on PyPI](https://pypi.org/project/agent-framework/)
