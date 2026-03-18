from google.adk.a2a.executor.a2a_agent_executor import A2aAgentExecutor
from google.adk.runners import Runner
from google.adk.artifacts.in_memory_artifact_service import InMemoryArtifactService
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.auth.credential_service.in_memory_credential_service import InMemoryCredentialService
from google.adk.agents.base_agent import BaseAgent

class AdkAgentToA2AExecutor(A2aAgentExecutor):
    """A wrapper around A2aAgentExecutor that initializes it with a basic runner for the given agent."""
    def __init__(self, agent: BaseAgent):
        def create_runner() -> Runner:
            return Runner(
                app_name=agent.name or "adk_agent",
                agent=agent,
                artifact_service=InMemoryArtifactService(),
                session_service=InMemorySessionService(),
                memory_service=InMemoryMemoryService(),
                credential_service=InMemoryCredentialService(),
            )
        super().__init__(runner=create_runner)
