"""Unit tests for discovering Orchestrator Reasoning Engine via Google Cloud Agent Registry."""

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

FAST_API_FE_DIR = Path(__file__).resolve().parent.parent / "fast-api-fe"
if str(FAST_API_FE_DIR) not in sys.path:
    sys.path.insert(0, str(FAST_API_FE_DIR))

with patch("vertexai.init"):
    from services import agent_client
    from services.agent_client import (
        _extract_reasoning_engine_id_from_agent_entry,
        resolve_orchestrator_engine_id,
        get_orchestrator_engine_id,
        list_user_sessions,
        get_session_history,
        query_agent,
    )


def test_extract_reasoning_engine_id_from_runtime_reference():
    """Verifies extraction from attributes RuntimeReference URI."""
    entry = {
        "agentId": "urn:agent:projects-48196429354:projects:48196429354:locations:us-central1:aiplatform:reasoningEngines:1818476233864773632",
        "displayName": "Orchestrator Agent",
        "attributes": {
            "agentregistry.googleapis.com/system/RuntimeReference": {
                "uri": "//aiplatform.googleapis.com/projects/48196429354/locations/us-central1/reasoningEngines/1818476233864773632"
            }
        },
    }
    expected = "projects/48196429354/locations/us-central1/reasoningEngines/1818476233864773632"
    assert _extract_reasoning_engine_id_from_agent_entry(entry) == expected


def test_extract_reasoning_engine_id_fallbacks():
    """Verifies extraction fallbacks from protocol interface URL and URN."""
    expected = "projects/48196429354/locations/us-central1/reasoningEngines/1818476233864773632"

    # Fallback 1: via protocols interfaces URL
    entry_proto = {
        "displayName": "Orchestrator Agent",
        "protocols": [
            {
                "type": "CUSTOM",
                "interfaces": [
                    {
                        "protocolBinding": "HTTP_JSON",
                        "url": "https://us-central1-aiplatform.googleapis.com/v1/projects/48196429354/locations/us-central1/reasoningEngines/1818476233864773632:streamQuery",
                    }
                ],
            }
        ],
    }
    assert _extract_reasoning_engine_id_from_agent_entry(entry_proto) == expected

    # Fallback 2: via card URL
    entry_card = {
        "displayName": "Orchestrator Agent",
        "card": {
            "content": {
                "url": "https://us-central1-aiplatform.googleapis.com/v1/projects/48196429354/locations/us-central1/reasoningEngines/1818476233864773632:query"
            }
        },
    }
    assert _extract_reasoning_engine_id_from_agent_entry(entry_card) == expected

    # Fallback 3: via agentId URN
    entry_urn = {
        "displayName": "Orchestrator Agent",
        "agentId": "urn:agent:projects-48196429354:projects:48196429354:locations:us-central1:aiplatform:reasoningEngines:1818476233864773632",
    }
    assert _extract_reasoning_engine_id_from_agent_entry(entry_urn) == expected

    # Empty/unknown metadata returns None
    assert _extract_reasoning_engine_id_from_agent_entry({}) is None


def test_resolve_orchestrator_engine_id_matches_display_name():
    """Verifies resolve_orchestrator_engine_id finds agent matching target display name."""
    mock_agents = [
        {"displayName": "Workspace Agent", "attributes": {}},
        {
            "name": "projects/p/locations/l/agents/orch-1",
            "displayName": "Orchestrator Agent",
            "attributes": {
                "agentregistry.googleapis.com/system/RuntimeReference": {
                    "uri": "//aiplatform.googleapis.com/projects/48196429354/locations/us-central1/reasoningEngines/1818476233864773632"
                }
            },
        },
        {"displayName": "bookings", "attributes": {}},
    ]

    mock_registry = MagicMock()
    mock_registry.list_agents.return_value = {"agents": mock_agents}

    with patch("services.agent_client.AgentRegistry", return_value=mock_registry):
        res = resolve_orchestrator_engine_id(
            project_id="test-proj",
            location="us-central1",
            target_display_name="Orchestrator Agent",
        )
    assert res == "projects/48196429354/locations/us-central1/reasoningEngines/1818476233864773632"


def test_resolve_orchestrator_engine_id_raises_when_missing():
    """Verifies resolve_orchestrator_engine_id raises RuntimeError if agent not found."""
    mock_registry = MagicMock()
    mock_registry.list_agents.return_value = {
        "agents": [{"displayName": "bookings"}]
    }

    with patch("services.agent_client.AgentRegistry", return_value=mock_registry):
        with pytest.raises(RuntimeError, match="Could not discover 'Orchestrator Agent'"):
            resolve_orchestrator_engine_id(
                project_id="test-proj",
                location="us-central1",
                target_display_name="Orchestrator Agent",
            )


def test_get_orchestrator_engine_id_caches_result():
    """Verifies in-memory caching in get_orchestrator_engine_id()."""
    target_engine_id = "projects/48196429354/locations/us-central1/reasoningEngines/1818476233864773632"

    with (
        patch.object(agent_client, "ENGINE_ID", None),
        patch.object(agent_client, "_RESOLVED_ENGINE_ID", None),
        patch.object(
            agent_client,
            "resolve_orchestrator_engine_id",
            return_value=target_engine_id,
        ) as mock_resolve,
    ):
        first = get_orchestrator_engine_id()
        assert first == target_engine_id
        assert mock_resolve.call_count == 1

        # Second call should use cached _RESOLVED_ENGINE_ID
        second = get_orchestrator_engine_id()
        assert second == target_engine_id
        assert mock_resolve.call_count == 1

        # Force refresh should invoke resolve again
        refreshed = get_orchestrator_engine_id(force_refresh=True)
        assert refreshed == target_engine_id
        assert mock_resolve.call_count == 2


@pytest.mark.asyncio
async def test_session_and_query_use_discovered_engine_id():
    """Verifies list_user_sessions, get_session_history, and query_agent use discovered engine ID."""
    discovered_id = "projects/48196429354/locations/us-central1/reasoningEngines/1818476233864773632"

    mock_client = MagicMock()
    mock_client.create_session = AsyncMock(
        return_value=SimpleNamespace(name=f"{discovered_id}/sessions/sess-discovered-1")
    )
    mock_client.get_session = AsyncMock(
        return_value=SimpleNamespace(user_id="user-1")
    )

    async def mock_events():
        yield SimpleNamespace(
            content=SimpleNamespace(
                role="model",
                parts=[SimpleNamespace(text="Hello from Orchestrator", thought=False)],
            )
        )

    mock_client.list_events = AsyncMock(return_value=mock_events())

    async def mock_sessions():
        yield SimpleNamespace(
            name=f"{discovered_id}/sessions/sess-1",
            user_id="user-1",
        )

    mock_client.list_sessions = AsyncMock(return_value=mock_sessions())

    mock_remote_app = MagicMock()
    mock_remote_app.stream_query.return_value = [
        {"content": {"role": "model", "parts": [{"text": "Hello, how can I help?"}]}}
    ]

    with (
        patch.object(agent_client, "ENGINE_ID", None),
        patch.object(agent_client, "get_orchestrator_engine_id", return_value=discovered_id),
        patch.object(agent_client, "_get_session_client", return_value=mock_client),
        patch("services.agent_client.agent_engines.get", return_value=mock_remote_app) as mock_agent_engines_get,
    ):
        # 1. list_user_sessions
        sessions = await list_user_sessions("user-1")
        assert len(sessions) == 1
        assert sessions[0]["id"] == "sess-1"

        # 2. get_session_history
        history = await get_session_history("user-1", "sess-1")
        assert len(history) == 1
        assert history[0]["content"] == "Hello from Orchestrator"

        # 3. query_agent
        reply, sess_id = await query_agent(
            user_message="Hi",
            user_id="user-1",
            session_id=None,
        )
        assert reply == "Hello, how can I help?"
        assert sess_id == "sess-discovered-1"
        mock_agent_engines_get.assert_called_once_with(discovered_id)


