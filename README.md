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

## 4. Run the interactive chat

```bash
python hello_agent.py
```

Type questions in the terminal. The conversation is kept in one
`AgentSession`, so the agent can use earlier messages. Type `exit` or `quit`
to stop.

After every response, the program prints input, output, and total token counts
from `AgentResponse.usage_details`.

## What to learn

- `SecretClient` reads the API key from Azure Key Vault.
- `OpenAIChatClient` connects Agent Framework to Azure OpenAI.
- `Agent` adds instructions and agent behavior around the client.
- `agent.create_session()` keeps the conversation history.
- `agent.run(...)` sends a user message and waits for the complete response.
- `result.usage_details` exposes token usage for observability.

References:

- [Microsoft Agent Framework: Your first agent](https://learn.microsoft.com/agent-framework/get-started/your-first-agent)
- [Agent Framework on PyPI](https://pypi.org/project/agent-framework/)
