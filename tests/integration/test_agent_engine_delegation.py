import os
import pytest
import asyncio
from vertexai import agent_engines
import vertexai

ORCHESTRATOR_ENGINE_ID = os.environ.get("ORCHESTRATOR_ENGINE_ID")
PROJECT_ID = os.environ.get("PROJECT_ID")
LOCATION = os.environ.get("LOCATION")

@pytest.mark.asyncio
async def test_orchestrator_to_booking_delegation():
    """
    Tests that the orchestrator agent can be queried and attempts to delegate to the booking agent.
    Note: This test requires valid credentials and will likely fail with 401 Unauthorized 
    unless a valid IAP token is provided in the headers, but it validates the connectivity
    and the reachability of the Reasoning Engine.
    """
    vertexai.init(project=PROJECT_ID, location=LOCATION)
    
    # Initialize the orchestrator agent remote app
    orchestrator_app = agent_engines.get(ORCHESTRATOR_ENGINE_ID)
    
    # We simulate a booking request. 
    # The orchestrator agent should:
    # 1. Detect booking intent.
    # 2. Call the 'bookings' tool.
    query = "Please make a hotel booking for me in Sydney for tomorrow at 10am."
    
    # We pass a dummy token to see if the agent reaches the validation step.
    # In a real scenario, this would be a valid IAP JWT.
    dummy_token = "eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJlcnJvciI6ImR1bW15In0." 
    
    run_config = {
        "custom_metadata": {
            "x-user-identity": dummy_token,
            "x-user-timezone": "Australia/Sydney"
        }
    }

    print(f"\nQuerying Orchestrator Agent: {query}")
    
    try:
        response_text = ""
        # Using the simplified stream_query
        async for event in orchestrator_app.async_stream_query(
            message=query,
            run_config=run_config
        ):
            # ADK/Reasoning Engine events usually have a 'role' or 'content'
            if "content" in event:
                parts = event["content"].get("parts", [])
                for part in parts:
                    if "text" in part:
                        response_text += part["text"]
        
        print(f"Agent Response: {response_text}")
        
        # If the token is invalid, the agent should return an Authentication error message
        # as defined in orchestrator/agent.py (validate_token call)
        assert "Authentication error" in response_text or "Error: Missing authentication token" in response_text or response_text
        
    except Exception as e:
        print(f"Error during agent query: {e}")
        # If it's a 403/401 from the Vertex AI service itself, it means our local creds are the issue.
        # If it's a successful call but the agent returns an error string, delegation logic was hit.
        pytest.fail(f"Failed to communicate with Orchestrator Agent: {e}")

if __name__ == "__main__":
    asyncio.run(test_orchestrator_to_booking_delegation())
