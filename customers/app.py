from vertexai.agent_engines import AdkApp
from customers.agent import create_agent

app = AdkApp(agent=create_agent())
