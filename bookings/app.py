from vertexai.agent_engines import AdkApp
from vertexai.preview.reasoning_engines import A2aAgent
from bookings.agent import create_agent, create_bookings_agent_card
from bookings.agent_executor import AdkAgentToA2AExecutor

def create_bookings_agent_executor() -> AdkAgentToA2AExecutor:
    """Factory function to create the A2A agent executor for the Bookings agent."""
    return AdkAgentToA2AExecutor(agent=create_agent())


# A2A Agent wrapper for Vertex AI Agent Engine deployment & Agent Registry indexing
a2a_app = A2aAgent(
    agent_card=create_bookings_agent_card(),
    agent_executor_builder=create_bookings_agent_executor,
)

# Use the factory function directly to ensure the agent is instantiated 
# during the server-side setup of the AdkApp, helping avoid loop pollution.
app = AdkApp(agent=create_agent())
