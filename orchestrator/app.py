from vertexai.agent_engines import AdkApp
from orchestrator.agent import create_agent

app = AdkApp(agent=create_agent())
