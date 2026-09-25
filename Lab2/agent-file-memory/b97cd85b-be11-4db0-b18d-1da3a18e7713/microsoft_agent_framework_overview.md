Microsoft Agent Framework (MAF) Overview

## Origins and Rationale

- **Evolution from Semantic Kernel and AutoGen**:
  - MAF unifies two earlier Microsoft frameworks:
    - *Semantic Kernel*: Enterprise-grade SDK featuring connectors for data systems, compliance, and production-level readiness.
    - *AutoGen*: Research-driven project introducing multi-agent orchestration patterns like Group Chat.
  - Combines the innovation and orchestration models of AutoGen with the reliability of Semantic Kernel.

- **Release Timeline**
  - Public Preview: October 2025
  - General Availability: April 3, 2026
  - Current Status: Actively developed with memory integrations and orchestration enhancements.

- **Deprecation of Prior Frameworks**:
  - Both Semantic Kernel and AutoGen are now in maintenance mode, receiving only critical updates and patches.

## Core Capabilities and Architecture

### Multi-Language Support
- .NET (C#), Python, and Go (the latter in public preview)

### Foundational Components
- **Agents**: Autonomous units powered by LLMs. Supports models from providers like Azure OpenAI, OpenAI, Anthropic, and Ollama.
- **Harness Agent**: Pre-built tool for executing long, multi-step workflows with features like to-do tracking, observability, and context storage.
- **Workflows**: Tool for graph-based and functional orchestration with explicit control flow through agents and operations.

### Tools, Middleware & Integrations
- Hosted tools: Code Interpreter, File Search, Web Search
- Custom tools: Support for @ai_function
- Interoperability standards: Model Context Protocol (MCP), OpenAPI.
- Middleware: Pipelines for request/response handling; exception handling, logging, etc.

### Memory Architecture
- Modular memory architecture through Chat History Memory Providers.
- Memory storage options include:
  - *Service-Managed*: Server-side conversation history storage with reference IDs.
  - *Client-Managed*: Client sends and manages conversation history for increased privacy.

### Orchestration Patterns
- Sequential execution (step-by-step)
- Concurrent execution
- Group Chat orchestration
- Handoff orchestration
- Magentic orchestration (a manager orchestrating subtasks)

### Ecosystem Interoperability
- Agent-to-Agent (A2A) communication
- MCP and OpenAPI integration
- Secure hosting on Azure Foundry
- Observability through OpenTelemetry for diagnostics
- RBAC and hosted session isolation for enterprise compliance.

### Recent Developments (2026)

- **Memory Expansion**: Integration with Azure Cosmos DB to enable cross-session memory.
- **Enhanced Secure Hosting**: Includes session and user isolation.
- **New Features**: Enhanced vector-store memory providers and tools for robust orchestration and security.

---

## Summary Comparison

| Feature               | Semantic Kernel / AutoGen    | Microsoft Agent Framework (MAF)  |
|-----------------------|------------------------------|-----------------------------------|
| Purpose               | SK: Enterprise-grade SDK; AG: Research on multi-agent patterns | Unified, production-ready framework |
| Development Status    | Maintenance mode             | Active development               |
| Supported Languages   | C# (.NET) - SK, Python - AG  | .NET, Python, Go (public preview)|
| Memory Management     | Limited memory options       | Modular memory with vector stores and Cosmos DB |
| Hosting & Security    | Minimal security features    | Enterprise-ready hosting with compliance |
| Orchestration         | Simplified execution paths   | Advanced workflows (Group Chat, Handoff, etc.) |

---

## Key Takeaways

1. Microsoft Agent Framework unifies and replaces Semantic Kernel and AutoGen.
2. It is designed for enterprise-scale agent development with dynamic memory, workflows, and hosting.
3. Features advanced multi-agent orchestration and interoperability built through MCP, OpenAPI, and A2A standards.
4. Includes out-of-the-box tools and support for creating, managing, and hosting agents for use cases like code execution, task orchestration, and conversation memory.