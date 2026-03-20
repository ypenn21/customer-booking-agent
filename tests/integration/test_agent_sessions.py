import pytest
import importlib
from fastapi.testclient import TestClient

# Import main by path or by dynamically loading the module if possible
# The project runs `fast-api-fe.main` using `uvicorn`, so let's try sys.path
import sys
import os

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, repo_root)

import importlib
main_module = importlib.import_module("fast-api-fe.main")
app = main_module.app


client = TestClient(app)

def test_session_lifecycle():
    # 1. Start a new session
    resp1 = client.post(
        "/v1/chat/completions",
        json={
            "model": "customers-agent",
            "messages": [{"role": "user", "content": "Hi"}],
            "force_new_session": True
        }
    )
    if resp1.status_code == 200:
        data = resp1.json()
        assert "session_id" in data
        session_id = data["session_id"]
        assert session_id is not None
        
        # 2. List sessions
        resp2 = client.get("/v1/sessions")
        assert resp2.status_code == 200
        sessions = resp2.json().get("sessions", [])
        print("Created session:", session_id)
        print("Listed sessions:", sessions)
        assert any(s["id"] == session_id for s in sessions)

        # 3. Resume session
        resp3 = client.post(
            "/v1/chat/completions",
            json={
                "model": "customers-agent",
                "messages": [{"role": "user", "content": "What is my name?"}],
                "force_new_session": False,
                "session_id": session_id
            }
        )
        assert resp3.status_code == 200
        assert resp3.json()["session_id"] == session_id
