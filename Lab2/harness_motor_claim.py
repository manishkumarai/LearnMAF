"""Multi-agent harness for a simulated motor insurance FNOL workflow.

The lead FNOL coordinator delegates work to specialist background agents for
intake validation, coverage review, damage triage, fraud-signal review, and
claims routing. The sample does not connect to a real policy or claims system
and must not be used to make automatic coverage, liability, fraud, or payment
decisions.
"""

import asyncio
import inspect
import time
from typing import Any

from agent_framework import Agent, AgentModeProvider, create_harness_agent
from agent_framework import todos_remaining, todos_remaining_message
from agent_framework.openai import OpenAIChatClient
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

try:
    from .harness_research import (
        ConsoleObservability,
        ModelObservabilityMiddleware,
        ToolObservabilityMiddleware,
        ask_for_full_observability,
        load_environment,
        required_environment_variable,
    )
except ImportError:
    from harness_research import (
        ConsoleObservability,
        ModelObservabilityMiddleware,
        ToolObservabilityMiddleware,
        ask_for_full_observability,
        load_environment,
        required_environment_variable,
    )


COORDINATOR_INSTRUCTIONS = """\
## Motor Insurance FNOL Coordinator

You coordinate a simulated First Notice of Loss (FNOL) process for motor
insurance claims. Help the user assemble a clear draft claim file and route it
for human review. You do not have access to a real policy administration,
claims, repair, police, medical, payment, or fraud system.

### Safety and decision boundaries

- If anyone may be injured, in danger, or blocking traffic, prioritize local
  emergency services and personal safety before claim administration.
- Never invent claim facts, policy terms, coverage, liability, repair costs,
  fraud findings, or payment amounts. Mark unknown information explicitly.
- Never approve or deny coverage, assign legal liability, accuse anyone of
  fraud, authorize repairs, or promise payment. Those decisions require an
  authorized human claims professional and applicable policy wording.
- Treat background-agent output as advisory analysis that must be verified.
- Request only information needed for FNOL. Discourage users from entering
  full payment-card numbers, bank credentials, government-ID numbers, medical
  records, or other unnecessary sensitive data.
- Clearly label this as a draft assessment and state that no real claim has
  been submitted by this sample.

### Intake behavior

Collect or identify the status of these items before finalizing the draft:

1. Policy number or another non-sensitive policy reference.
2. Insured/contact name and a safe contact method, with minimal personal data.
3. Date, time, country/jurisdiction, and exact or approximate loss location.
4. Insured vehicle and other vehicles or property involved.
5. A factual incident description without assumptions about fault.
6. Injuries, emergency response, police report, witnesses, and third parties.
7. Vehicle condition, drivability, towing/storage location, and visible damage.
8. Available evidence such as photos, video, dashcam, and exchange details.

Ask concise follow-up questions for material missing information. Do not block
urgent safety guidance while collecting details.

### Multi-agent execution

When there is enough information for a useful assessment, create todos and use
the background-agent tools. Start independent specialist tasks concurrently:

- `FNOLIntakeSpecialist` for completeness and a normalized loss summary.
- `CoverageReviewSpecialist` for policy questions and coverage uncertainties.
- `DamageTriageSpecialist` for safety, severity, towing, and inspection needs.
- `FraudSignalSpecialist` for neutral inconsistencies and verification needs.

Wait for every task, retrieve every result, and clear completed tasks. Then ask
`ClaimsRoutingSpecialist` to recommend the human review path using the combined
specialist findings. Wait for and retrieve that result too. Never finish while
a background task is still running.

### Final draft FNOL report

Present a concise report with these sections:

1. Draft status and prominent no-submission disclaimer.
2. Loss snapshot and known parties/vehicles.
3. Immediate safety and vehicle-handling actions.
4. Intake completeness and missing information.
5. Coverage questions requiring policy verification.
6. Damage triage and inspection recommendation.
7. Neutral inconsistencies or fraud-review indicators, without accusations.
8. Recommended human routing, priority, and next actions.
9. Documents/evidence checklist.
10. Specialist contributions and assumptions.

Save the final draft report to file memory for later turns.
"""


SPECIALISTS = (
    (
        "FNOLIntakeSpecialist",
        "Validates FNOL completeness and produces a normalized factual loss summary.",
        """You are a motor-claim FNOL intake specialist. Extract only supplied
facts, normalize them into a structured loss summary, identify missing required
fields, and list concise follow-up questions. Separate confirmed facts from
user statements and unknowns. Prioritize injuries and immediate safety. Do not
decide coverage, liability, fraud, or payment, and do not claim that a real
insurance record has been created.""",
    ),
    (
        "CoverageReviewSpecialist",
        "Identifies policy and coverage questions that need human verification.",
        """You are a motor-policy review specialist. Based only on the supplied
claim facts, identify policy data, insured vehicle/driver status, dates,
endorsements, deductibles, limits, exclusions, and jurisdictional questions
that an authorized adjuster must verify. Never infer missing policy wording or
approve/deny coverage. Return facts, unknowns, possible coverage paths stated
conditionally, and required verification steps.""",
    ),
    (
        "DamageTriageSpecialist",
        "Assesses safety, drivability, towing, inspection, and damage severity indicators.",
        """You are a motor physical-damage triage specialist. Review reported
damage, warning lights, fluid leaks, airbags, wheel/suspension condition,
drivability, towing/storage, and evidence availability. Recommend safe next
steps and an inspection path. Never provide a repair authorization, guaranteed
estimate, total-loss decision, or coverage decision. Escalate injury, fire,
battery, fuel-leak, and unsafe-driving concerns.""",
    ),
    (
        "FraudSignalSpecialist",
        "Reviews inconsistencies and verification needs without making fraud accusations.",
        """You are a claim-integrity review specialist. Identify only objective
inconsistencies, missing corroboration, duplication indicators, timing issues,
or evidence gaps in the supplied facts. Offer benign explanations where
reasonable and propose proportionate verification. Never label a person or
claim fraudulent and never recommend adverse action solely from an automated
signal. State when no meaningful indicator is present.""",
    ),
    (
        "ClaimsRoutingSpecialist",
        "Recommends priority, ownership, and next steps for human claims handling.",
        """You are a motor-claims routing specialist. Given the coordinator's
combined specialist findings, recommend a human handling path, priority,
skills needed, dependencies, and next actions. Account for injuries, vehicle
safety, third parties, towing/storage, coverage uncertainty, and verification
needs. Never make a final coverage, liability, fraud, reserve, repair, or
payment decision.""",
    ),
)


BACKGROUND_AGENT_INSTRUCTIONS = """\
## FNOL Specialist Agents

Use the background-agent tools to delegate the motor FNOL assessment.
Independent reviews should be started concurrently. Always wait for all
outstanding tasks, retrieve their results, and clear completed tasks. Treat
specialist results as advisory and reconcile disagreements explicitly.

{background_agents}
"""


def build_client(
    *,
    api_key: str,
    azure_endpoint: str,
    deployment_name: str,
    observer: ConsoleObservability,
    agent_label: str,
) -> OpenAIChatClient:
    """Create an observed Azure OpenAI client for one named agent."""
    return OpenAIChatClient(
        api_key=api_key,
        azure_endpoint=azure_endpoint,
        model=deployment_name,
        middleware=[
            ModelObservabilityMiddleware(observer, agent_label),
            ToolObservabilityMiddleware(observer, agent_label),
        ],
    )


def build_specialist_agents(
    *,
    api_key: str,
    azure_endpoint: str,
    deployment_name: str,
    observer: ConsoleObservability,
) -> list[Agent]:
    """Build the trusted specialist agents available to the coordinator."""
    agents = []
    for name, description, instructions in SPECIALISTS:
        agents.append(
            Agent(
                client=build_client(
                    api_key=api_key,
                    azure_endpoint=azure_endpoint,
                    deployment_name=deployment_name,
                    observer=observer,
                    agent_label=name,
                ),
                name=name,
                description=description,
                instructions=instructions,
                # Keep each specialist's history local. Azure response IDs may
                # not remain available for later or follow-up calls.
                default_options={"store": False},
            )
        )
    return agents


async def main() -> None:
    observer = ConsoleObservability()
    observer.event("STARTUP", "Loading environment configuration")
    loaded_files = load_environment()
    observer.event(
        "CONFIG",
        "Loaded: " + ", ".join(str(path) for path in loaded_files),
    )

    azure_endpoint = required_environment_variable("AZURE_OPENAI_ENDPOINT")
    deployment_name = required_environment_variable("AZURE_OPENAI_DEPLOYMENT")
    observer.event(
        "CONFIG",
        f"Azure endpoint={azure_endpoint}; deployment={deployment_name}",
    )

    credential_started = time.perf_counter()
    observer.event("AUTH", "Reading AZURE-OPENAI-API-KEY from Azure Key Vault")
    key_vault = SecretClient(
        vault_url="https://kv-mkbhopal919174214256.vault.azure.net/",
        credential=DefaultAzureCredential(),
    )
    api_key = key_vault.get_secret("AZURE-OPENAI-API-KEY").value
    observer.event(
        "AUTH",
        f"Key Vault secret retrieved in {time.perf_counter() - credential_started:.2f}s",
    )

    observer.event("STARTUP", "Building five motor-claim specialist agents")
    specialists = build_specialist_agents(
        api_key=api_key,
        azure_endpoint=azure_endpoint,
        deployment_name=deployment_name,
        observer=observer,
    )

    coordinator_client = build_client(
        api_key=api_key,
        azure_endpoint=azure_endpoint,
        deployment_name=deployment_name,
        observer=observer,
        agent_label="FNOLCoordinator",
    )

    base_should_continue = todos_remaining(looping_modes=["execute"])

    async def observed_should_continue(**kwargs) -> Any:
        result = base_should_continue(**kwargs)
        if inspect.isawaitable(result):
            result = await result
        iteration = kwargs.get("iteration", 0)
        observer.loop_iterations = max(observer.loop_iterations, iteration)
        decision = result[0] if isinstance(result, tuple) else result
        feedback = result[1] if isinstance(result, tuple) and len(result) > 1 else None
        observer.event(
            "LOOP DECISION",
            (
                f"pass={iteration}, todos remain={bool(decision)}, "
                f"action={'continue automatically' if decision else 'return to user'}, "
                f"feedback={feedback or 'none'}"
            ),
        )
        return result

    async def observed_next_message(**kwargs) -> Any:
        message = todos_remaining_message(**kwargs)
        if inspect.isawaitable(message):
            message = await message
        observer.event(
            "LOOP INPUT",
            f"Starting the next autonomous pass with: {message or 'previous input'}",
        )
        return message

    observer.event("STARTUP", "Building the lead FNOL coordinator harness")
    coordinator = create_harness_agent(
        client=coordinator_client,
        name="FNOLCoordinator",
        description=(
            "Coordinates a simulated motor insurance First Notice of Loss "
            "assessment using specialist agents."
        ),
        agent_instructions=COORDINATOR_INSTRUCTIONS,
        mode_provider=AgentModeProvider(default_mode="plan"),
        background_agents=specialists,
        background_agents_instructions=BACKGROUND_AGENT_INSTRUCTIONS,
        background_agents_wait_timeout_seconds=120,
        disable_web_search=True,
        max_context_window_tokens=128_000,
        max_output_tokens=16_384,
        loop_should_continue=observed_should_continue,
        loop_next_message=observed_next_message,
        loop_max_iterations=12,
        # Replay local history rather than chaining Azure previous_response_id.
        default_options={"store": False},
    )

    session = coordinator.create_session()
    observer.event(
        "READY",
        (
            f"Agent={coordinator.name}; specialists={len(specialists)}; "
            f"session_id={session.session_id}; initial mode=plan"
        ),
    )
    print("Motor FNOL coordinator ready in plan mode. Type 'exit' to stop.")
    print("Describe a motor loss, review the plan, then ask the agent to execute it.")
    print("This demo drafts an assessment only; it does not submit a real claim.")
    print(
        "Observability includes coordinator, specialist, tool, token, and timing "
        "events; private model chain-of-thought is not exposed."
    )

    while True:
        try:
            question = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if question.lower() in {"exit", "quit"}:
            break
        if not question:
            continue

        try:
            full_observability = ask_for_full_observability()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        observer.start_turn(
            question,
            full_observability=full_observability,
        )
        try:
            # A previous failed run may have left a stale Azure response ID.
            session.service_session_id = None
            response_stream = coordinator.run(
                question,
                stream=True,
                session=session,
            )
            async for update in response_stream:
                observer.stream_update(update)
            result = await response_stream.get_final_response()
        except Exception as error:
            elapsed = time.perf_counter() - observer.turn_started
            observer.event(
                "TURN ERROR",
                f"turn={observer.turn_number}, elapsed={elapsed:.2f}s, error={error!r}",
                force=True,
            )
            continue

        observer.finish_turn(result)

    if observer.full_observability:
        observer.event(
            "SHUTDOWN",
            (
                f"Completed {observer.turn_number} turn(s) in "
                f"{time.perf_counter() - observer.program_started:.2f}s; "
                f"session tokens: {observer.usage_line(observer.session_usage)}"
            ),
        )
    else:
        print("\nMotor FNOL coordinator stopped.")


if __name__ == "__main__":
    asyncio.run(main())
