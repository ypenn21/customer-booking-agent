# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Unit tests for mTLS-aware Agent Registry discovery and A2A client integration."""

import ssl
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from orchestrator.a2a_discovery import (
    MtlsAwareAgentRegistry,
    RegistryDiscoveredA2aAgent,
    _create_placeholder_bookings_card,
    _get_mtls_ssl_context,
    _to_mtls_url,
)


def test_to_mtls_url_rewrites_googleapis_hosts() -> None:
    """Verifies standard googleapis.com and sandbox.googleapis.com URLs rewrite to .mtls."""
    assert (
        _to_mtls_url(
            "https://agentregistry.googleapis.com/v1alpha/projects/p/locations/us-central1/agents"
        )
        == "https://agentregistry.mtls.googleapis.com/v1alpha/projects/p/locations/us-central1/agents"
    )
    assert (
        _to_mtls_url(
            "https://us-central1-aiplatform.googleapis.com/v1beta1/projects/p/locations/us-central1/reasoningEngines/123/a2a"
        )
        == "https://us-central1-aiplatform.mtls.googleapis.com/v1beta1/projects/p/locations/us-central1/reasoningEngines/123/a2a"
    )
    assert (
        _to_mtls_url("https://foo.sandbox.googleapis.com/v1/bar")
        == "https://foo.mtls.sandbox.googleapis.com/v1/bar"
    )


def test_to_mtls_url_preserves_existing_mtls_and_non_google_urls() -> None:
    """Verifies .mtls.googleapis.com and non-googleapis URLs remain unchanged."""
    mtls_url = "https://agentregistry.mtls.googleapis.com/v1alpha/projects/p/locations/us-central1/agents"
    assert _to_mtls_url(mtls_url) == mtls_url

    local_url = "http://localhost:8000/a2a"
    assert _to_mtls_url(local_url) == local_url


def test_get_mtls_ssl_context_returns_context_when_enabled() -> None:
    """Verifies _get_mtls_ssl_context returns SSLContext when client cert is active."""
    dummy_ctx = ssl.create_default_context()
    with (
        patch(
            "orchestrator.a2a_discovery.mtls.get_default_ssl_context",
            return_value=dummy_ctx,
        ),
        patch(
            "orchestrator.a2a_discovery.mtls.should_use_mtls_endpoint",
            return_value=True,
        ),
    ):
        assert _get_mtls_ssl_context() is dummy_ctx


def test_get_mtls_ssl_context_returns_none_when_disabled() -> None:
    """Verifies _get_mtls_ssl_context returns None when client cert is unavailable or disabled."""
    with patch(
        "orchestrator.a2a_discovery.mtls.get_default_ssl_context",
        return_value=None,
    ):
        assert _get_mtls_ssl_context() is None

    dummy_ctx = ssl.create_default_context()
    with (
        patch(
            "orchestrator.a2a_discovery.mtls.get_default_ssl_context",
            return_value=dummy_ctx,
        ),
        patch(
            "orchestrator.a2a_discovery.mtls.should_use_mtls_endpoint",
            return_value=False,
        ),
    ):
        assert _get_mtls_ssl_context() is None


def test_mtls_aware_agent_registry_uses_mtls_url_and_verify() -> None:
    """Verifies MtlsAwareAgentRegistry._make_request uses .mtls.googleapis.com and SSLContext."""
    dummy_ctx = ssl.create_default_context()
    mock_creds = MagicMock()
    mock_creds.token = "cba-token-123"
    mock_creds.quota_project_id = "agent-security-patterns"

    captured_init: dict[str, Any] = {}
    captured_get: dict[str, Any] = {}

    class DummyClient:
        def __init__(self, **kwargs: Any) -> None:
            captured_init.update(kwargs)

        def __enter__(self) -> "DummyClient":
            return self

        def __exit__(self, *args: Any) -> None:
            pass

        def get(self, url: str, headers: dict[str, str], params: Any = None) -> Any:
            captured_get["url"] = url
            captured_get["headers"] = headers
            captured_get["params"] = params
            resp = MagicMock()
            resp.raise_for_status.return_value = None
            resp.json.return_value = {"agents": []}
            return resp

    with (
        patch(
            "orchestrator.a2a_discovery.google.auth.default",
            return_value=(mock_creds, "agent-security-patterns"),
        ),
        patch(
            "orchestrator.a2a_discovery._get_mtls_ssl_context",
            return_value=dummy_ctx,
        ),
        patch("orchestrator.a2a_discovery.httpx.Client", DummyClient),
    ):
        registry = MtlsAwareAgentRegistry(
            project_id="agent-security-patterns",
            location="us-central1",
        )
        result = registry.list_agents()

    assert result == {"agents": []}
    assert captured_init["verify"] is dummy_ctx
    assert (
        captured_get["url"]
        == "https://agentregistry.mtls.googleapis.com/v1alpha/projects/agent-security-patterns/locations/us-central1/agents"
    )
    assert captured_get["headers"]["Authorization"] == "Bearer cba-token-123"


@pytest.mark.asyncio
async def test_registry_discovered_a2a_agent_rewrites_card_url_for_mtls() -> None:
    """Verifies RegistryDiscoveredA2aAgent rewrites card.url to .mtls.googleapis.com when mTLS is active."""
    dummy_ctx = ssl.create_default_context()
    card = _create_placeholder_bookings_card("Bookings test description")
    card.url = "https://us-central1-aiplatform.googleapis.com/v1beta1/projects/48196429354/locations/us-central1/reasoningEngines/697851783812218880/a2a"

    agent = RegistryDiscoveredA2aAgent(
        name="bookings",
        project_id="agent-security-patterns",
        location="us-central1",
        agent_card=card,
        discovered_from_registry=True,
    )

    captured_async_client_kwargs: dict[str, Any] = {}

    class DummyAsyncClient:
        def __init__(self, **kwargs: Any) -> None:
            captured_async_client_kwargs.update(kwargs)

        async def __aenter__(self) -> "DummyAsyncClient":
            return self

        async def __aexit__(self, *args: Any) -> None:
            pass

    async def empty_super_run(self_obj: Any, ctx: Any):
        if False:
            yield ctx

    mock_ctx = MagicMock()
    mock_ctx.invocation_id = "inv-1"
    mock_ctx.branch = None

    with (
        patch.object(agent, "_validate_caller_jwt", return_value=None),
        patch(
            "orchestrator.a2a_discovery._get_mtls_ssl_context",
            return_value=dummy_ctx,
        ),
        patch("orchestrator.a2a_discovery.GoogleADCAuth", return_value=MagicMock()),
        patch("orchestrator.a2a_discovery.httpx.AsyncClient", DummyAsyncClient),
        patch("orchestrator.a2a_discovery.A2AClientFactory") as mock_factory_cls,
        patch(
            "google.adk.agents.remote_a2a_agent.RemoteA2aAgent._run_async_impl",
            empty_super_run,
        ),
    ):
        mock_factory_cls.return_value.create.return_value = MagicMock()
        events = [event async for event in agent._run_async_impl(mock_ctx)]

    assert events == []
    assert (
        agent._agent_card.url
        == "https://us-central1-aiplatform.mtls.googleapis.com/v1beta1/projects/48196429354/locations/us-central1/reasoningEngines/697851783812218880/a2a"
    )
    assert captured_async_client_kwargs["verify"] is dummy_ctx
