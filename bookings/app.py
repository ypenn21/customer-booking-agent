from vertexai.agent_engines import AdkApp
from bookings.agent import create_agent

# Use the factory function directly to ensure the agent is instantiated 
# during the server-side setup of the AdkApp, helping avoid loop pollution.
app = AdkApp(agent=create_agent())
