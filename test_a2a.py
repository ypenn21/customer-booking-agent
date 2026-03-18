from google.adk.agents import Agent
from google.adk.models import Gemini
from google.adk.a2a.utils.agent_to_a2a import to_a2a
import asyncio

agent = Agent(name="test", model=Gemini(model="gemini-3-flash-preview"))
a2a_app = to_a2a(agent, port=8000)

from fastapi import FastAPI
app = FastAPI()
app.mount("/a2a/app", a2a_app)

print([r.path for r in app.routes])
