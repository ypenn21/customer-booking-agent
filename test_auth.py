import httpx
import google.auth
from google.auth.transport.requests import Request
import asyncio

class GoogleAuth(httpx.Auth):
    def __init__(self):
        self.credentials, self.project_id = google.auth.default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )

    def auth_flow(self, request):
        if not self.credentials.valid:
            self.credentials.refresh(Request())
        request.headers["Authorization"] = f"Bearer {self.credentials.token}"
        yield request

async def main():
    async with httpx.AsyncClient(auth=GoogleAuth()) as client:
        agent_card="https://us-central1-aiplatform.googleapis.com/v1/projects/genai-apps-25/locations/us-central1/reasoningEngines/9162713079862001664"
        response = await client.get(agent_card)
        print("Status code:", response.status_code)

if __name__ == "__main__":
    asyncio.run(main())
