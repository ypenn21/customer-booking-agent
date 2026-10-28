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

"""Agent Registry discovery and A2A client integration for the Orchestrator agent."""

from __future__ import annotations

import logging
import os
import ssl
from typing import Any, AsyncGenerator, Callable, Optional
from urllib.parse import urlparse, urlunparse

from a2a.client.client import ClientConfig as A2AClientConfig
from a2a.client.client_factory import ClientFactory as A2AClientFactory
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
    Message as A2AMessage,
    Part as A2APart,
    TransportProtocol,
)
import google.auth
from google.auth.transport import mtls
import google.auth.transport.requests
from google.adk.a2a.agent._remote_a2a_agent import (
    A2A_METADATA_PREFIX,
    _without_credential_parts,
)
from google.adk.agents.invocation_context import InvocationContext
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent
from google.adk.events.event import Event
from google.adk.flows.llm_flows.context._fencing import (
    _present_other_agent_message,
)
from google.adk.integrations.agent_registry import AgentRegistry
from google.adk.integrations.agent_registry.agent_registry import (
    AGENT_REGISTRY_BASE_URL,
)
from google.genai import types as genai_types
import httpx
import jwt
from pydantic import PrivateAttr

try:
    from .security import validate_token
except ImportError:
    from security import validate_token

logger = logging.getLogger(__name__)


def _to_mtls_url(url: str) -> str:
    """Rewrites a *.googleapis.com URL to its *.mtls.googleapis.com endpoint."""
    parsed = urlparse(url)
    netloc = parsed.netloc
    if netloc.endswith((".mtls.googleapis.com", ".mtls.sandbox.googleapis.com")):
        return url
    for domain in ("sandbox.googleapis.com", "googleapis.com"):
        if netloc.endswith("." + domain):
            netloc = netloc[: -len(domain)] + "mtls." + domain
            return urlunparse(parsed._replace(netloc=netloc))
    return url


def _get_mtls_ssl_context() -> Optional[ssl.SSLContext]:
    """Returns an SSLContext loaded with the default workload client certificate if active."""
    get_ctx_fn = getattr(mtls, "get_default_ssl_context", None)
    if get_ctx_fn is None:
        return None
    try:
        ctx = get_ctx_fn()
    except Exception as exc:
        logger.warning(
            "Failed to load default mTLS SSL context from google-auth: %s", exc
        )
        return None
    if ctx is None:
        return None
    should_use_mtls = getattr(mtls, "should_use_mtls_endpoint", None)
    if should_use_mtls is not None:
        try:
            if not should_use_mtls(client_cert_available=True):
                return None
        except Exception as exc:
            logger.warning("Failed checking should_use_mtls_endpoint: %s", exc)
    return ctx


class MtlsAwareAgentRegistry(AgentRegistry):
    """AgentRegistry client that supports certificate-bound mTLS tokens under AGENT_IDENTITY."""

    def __init__(
        self,
        project_id: str | None = None,
        location: str | None = None,
        header_provider: Callable[[ReadonlyContext], dict[str, str]] | None = None,
    ) -> None:
        super().__init__(
            project_id=project_id,
            location=location,
            header_provider=header_provider,
        )
        try:
            self._credentials, _ = google.auth.default(
                scopes=["https://www.googleapis.com/auth/cloud-platform"]
            )
        except google.auth.exceptions.DefaultCredentialsError as exc:
            raise RuntimeError(
                f"Failed to get default Google Cloud credentials: {exc}"
            ) from exc

    def _make_request(
        self, path: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Makes GET requests to Agent Registry using mTLS when a workload client cert is active."""
        if path.startswith("projects/"):
            url = f"{AGENT_REGISTRY_BASE_URL}/{path}"
        else:
            url = f"{AGENT_REGISTRY_BASE_URL}/{self._base_path}/{path}"

        mtls_ssl_ctx = _get_mtls_ssl_context()
        if mtls_ssl_ctx is not None:
            url = _to_mtls_url(url)

        try:
            headers = self._get_auth_headers()
            verify: bool | ssl.SSLContext = (
                mtls_ssl_ctx if mtls_ssl_ctx is not None else True
            )
            with httpx.Client(verify=verify, timeout=30.0) as client:
                response = client.get(url, headers=headers, params=params)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            raise RuntimeError(
                f"API request failed with status {e.response.status_code}:"
                f" {e.response.text}"
            ) from e
        except httpx.RequestError as e:
            raise RuntimeError(f"API request failed (network error): {e}") from e
        except Exception as e:
            raise RuntimeError(f"API request failed: {e}") from e


class GoogleADCAuth(httpx.Auth):
    """Attaches a refreshed Google Cloud Bearer token to outgoing A2A HTTP requests."""

    def __init__(self) -> None:
        self._credentials, _ = google.auth.default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        self._auth_request = google.auth.transport.requests.Request()

    def auth_flow(self, request: httpx.Request):
        if not self._credentials.valid or not self._credentials.token:
            self._credentials.refresh(self._auth_request)
        request.headers["Authorization"] = f"Bearer {self._credentials.token}"
        quota_project_id = getattr(self._credentials, "quota_project_id", None)
        if quota_project_id and "x-goog-user-project" not in request.headers:
            request.headers["x-goog-user-project"] = quota_project_id
        yield request


def _extract_custom_metadata_value(
    ctx: InvocationContext, key: str, default: Any = None
) -> Any:
    """Extracts a metadata key from InvocationContext.run_config.custom_metadata."""
    if not ctx.run_config or not ctx.run_config.custom_metadata:
        return default
    custom_meta = ctx.run_config.custom_metadata
    if key in custom_meta:
        return custom_meta[key]
    a2a_meta = custom_meta.get("a2a_metadata")
    if isinstance(a2a_meta, dict) and key in a2a_meta:
        return a2a_meta[key]
    return default


def forward_user_context_metadata(
    ctx: InvocationContext, message: A2AMessage
) -> dict[str, Any]:
    """Propagates x-user-identity (IAP JWT) and x-user-timezone into A2A request metadata."""
    del message  # Unused
    metadata: dict[str, Any] = {}
    token = _extract_custom_metadata_value(ctx, "x-user-identity")
    timezone = _extract_custom_metadata_value(ctx, "x-user-timezone", "UTC")
    if token:
        metadata["x-user-identity"] = token
    if timezone:
        metadata["x-user-timezone"] = timezone
    return metadata


def resolve_bookings_agent_card_from_registry(
    project_id: str,
    location: str,
    target_display_name: str = "Booking Assistant",
) -> AgentCard:
    """Queries Google Cloud Agent Registry and returns the resolved AgentCard for Bookings."""
    registry = MtlsAwareAgentRegistry(project_id=project_id, location=location)

    agent_registry_name = os.environ.get("BOOKINGS_AGENT_REGISTRY_NAME")
    if not agent_registry_name:
        filter_str = os.environ.get("BOOKINGS_REGISTRY_FILTER")
        response = registry.list_agents(filter_str=filter_str)
        agents = response.get("agents", [])
        matched_agent = None
        for entry in agents:
            display_name = entry.get("displayName", "")
            card_name = entry.get("card", {}).get("content", {}).get("name", "")
            if (
                target_display_name.lower() in display_name.lower()
                or "booking" in display_name.lower()
                or "booking" in card_name.lower()
            ):
                matched_agent = entry
                break

        if not matched_agent:
            raise RuntimeError(
                f"Could not discover '{target_display_name}' in Agent Registry "
                f"(project={project_id}, location={location}). Found agents: "
                f"{[a.get('displayName') for a in agents]}"
            )
        agent_registry_name = matched_agent["name"]
        logger.info(
            "Discovered Bookings agent in Agent Registry: %s (displayName=%s)",
            agent_registry_name,
            matched_agent.get("displayName"),
        )

    discovered_remote_agent = registry.get_remote_a2a_agent(
        agent_name=agent_registry_name
    )
    if not discovered_remote_agent._agent_card:
        raise RuntimeError(
            f"Agent Registry entry '{agent_registry_name}' did not produce a valid AgentCard."
        )
    return discovered_remote_agent._agent_card


def _create_placeholder_bookings_card(description: str) -> AgentCard:
    """Creates a placeholder AgentCard before runtime Agent Registry resolution."""
    skill = AgentSkill(
        id="manage_bookings_and_calendar",
        name="Manage Bookings and Calendar Invites",
        description=description,
        tags=["bookings", "travel", "flights", "hotels", "calendar"],
    )
    return AgentCard(
        name="bookings",
        description=description,
        url="http://localhost:8000/a2a",
        version="1.0.0",
        default_input_modes=["text/plain"],
        default_output_modes=["text/plain"],
        capabilities=AgentCapabilities(streaming=False),
        skills=[skill],
        preferred_transport=TransportProtocol.http_json,
    )


class RegistryDiscoveredA2aAgent(RemoteA2aAgent):
    """RemoteA2aAgent backed by Google Cloud Agent Registry with per-request ADC auth and loop isolation."""

    _project_id: Optional[str] = PrivateAttr(default=None)
    _location: str = PrivateAttr(default="us-central1")
    _target_display_name: str = PrivateAttr(default="Booking Assistant")
    _discovered_from_registry: bool = PrivateAttr(default=False)

    def __init__(
        self,
        *,
        name: str = "bookings",
        description: str = (
            "An agent that helps users make custom bookings, travel reservations, "
            "and schedule Microsoft Calendar invites."
        ),
        project_id: Optional[str] = None,
        location: str = "us-central1",
        target_display_name: str = "Booking Assistant",
        agent_card: Optional[AgentCard] = None,
        discovered_from_registry: bool = False,
        full_history_when_stateless: bool = True,
        **kwargs: Any,
    ) -> None:
        resolved_card = agent_card or _create_placeholder_bookings_card(description)
        super().__init__(
            name=name,
            agent_card=resolved_card,
            description=description,
            a2a_request_meta_provider=forward_user_context_metadata,
            full_history_when_stateless=full_history_when_stateless,
            **kwargs,
        )
        self._project_id = project_id
        self._location = location
        self._target_display_name = target_display_name
        self._discovered_from_registry = discovered_from_registry

    def _create_a2a_request_for_user_function_response(
        self, ctx: InvocationContext
    ) -> Optional[A2AMessage]:
        """Avoids resuming worker-local A2A task IDs when stateless history forwarding is enabled."""
        if self._full_history_when_stateless:
            return None
        return super()._create_a2a_request_for_user_function_response(ctx)

    def _get_resumable_task_id(
        self, ctx: InvocationContext, context_id: Optional[str]
    ) -> Optional[str]:
        """Prevents attaching worker-local task IDs when stateless history forwarding is enabled."""
        if self._full_history_when_stateless:
            return None
        return super()._get_resumable_task_id(ctx, context_id)

    def _construct_message_parts_from_session(
        self, ctx: InvocationContext
    ) -> tuple[list[A2APart], Optional[str]]:
        """Builds A2A message parts with full session history and no worker-pinned context_id."""
        if not self._full_history_when_stateless or not ctx.session or not ctx.session.events:
            return super()._construct_message_parts_from_session(ctx)

        rewritten_events: list[Event] = []
        for event in ctx.session.events:
            if self._is_remote_response(event):
                scrubbed = _without_credential_parts(event)
                presented = _present_other_agent_message(scrubbed)
                if presented is not None:
                    rewritten_events.append(presented)
            elif event.custom_metadata and (
                A2A_METADATA_PREFIX + "context_id" in event.custom_metadata
                or A2A_METADATA_PREFIX + "task_id" in event.custom_metadata
            ):
                cleaned_event = event.model_copy(deep=True)
                if cleaned_event.custom_metadata:
                    cleaned_event.custom_metadata.pop(
                        A2A_METADATA_PREFIX + "context_id", None
                    )
                    cleaned_event.custom_metadata.pop(
                        A2A_METADATA_PREFIX + "task_id", None
                    )
                rewritten_events.append(cleaned_event)
            else:
                rewritten_events.append(event)

        original_events = ctx.session.events
        try:
            ctx.session.events = rewritten_events
            message_parts, _ = super()._construct_message_parts_from_session(ctx)
            return message_parts, None
        finally:
            ctx.session.events = original_events

    def _ensure_registry_card_resolved(self) -> None:
        """Resolves the latest AgentCard from Google Cloud Agent Registry if not yet resolved."""
        if self._discovered_from_registry and self._agent_card:
            return
        project_id = self._project_id or os.environ.get("GOOGLE_CLOUD_PROJECT")
        location = (
            self._location
            or os.environ.get("LOCATION")
            or os.environ.get("AGENT_REGISTRY_LOCATION", "us-central1")
        )
        if not project_id:
            raise RuntimeError(
                "GOOGLE_CLOUD_PROJECT must be set to discover agents in Agent Registry."
            )
        card = resolve_bookings_agent_card_from_registry(
            project_id=project_id,
            location=location,
            target_display_name=self._target_display_name,
        )
        self._agent_card = card
        if card.description:
            self.description = card.description
        self._discovered_from_registry = True

    def _validate_caller_jwt(self, ctx: InvocationContext) -> Optional[str]:
        """Validates the caller's IAP JWT before delegating over A2A.

        Returns None if valid, or an error string if validation fails.
        """
        received_token = _extract_custom_metadata_value(ctx, "x-user-identity")
        iap_expected_audience = os.environ.get("IAP_EXPECTED_AUDIENCE")

        if not received_token:
            return "Error: Missing authentication token (x-user-identity)."
        if not iap_expected_audience:
            return "Error: Orchestrator agent audience (IAP_EXPECTED_AUDIENCE) not configured."

        try:
            try:
                decoded_claims = jwt.decode(
                    received_token, options={"verify_signature": False}
                )
                logger.info("Orchestrator Agent: Decoded claims: %s", decoded_claims)
            except Exception as decode_err:
                logger.error(
                    "Orchestrator Agent: Failed to decode received token: %s",
                    decode_err,
                )

            validate_token(received_token, iap_expected_audience)
            logger.info(
                "Successfully validated token in Orchestrator before A2A delegation."
            )
            return None
        except Exception as exc:
            logger.exception("Token validation failed before A2A delegation.")
            return f"Authentication error: {exc}"

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        """Validates user JWT, resolves Agent Registry endpoint, and runs A2A call in current loop."""
        auth_error = self._validate_caller_jwt(ctx)
        if auth_error:
            yield Event(
                author=self.name,
                content=genai_types.Content(
                    role="model",
                    parts=[genai_types.Part(text=auth_error)],
                ),
                invocation_id=ctx.invocation_id,
                branch=ctx.branch,
            )
            return

        try:
            self._ensure_registry_card_resolved()
        except Exception as exc:
            error_msg = f"Failed to discover bookings agent in Agent Registry: {exc}"
            logger.exception(error_msg)
            yield Event(
                author=self.name,
                content=genai_types.Content(
                    role="model",
                    parts=[genai_types.Part(text=error_msg)],
                ),
                invocation_id=ctx.invocation_id,
                branch=ctx.branch,
            )
            return

        mtls_ssl_ctx = _get_mtls_ssl_context()
        if mtls_ssl_ctx is not None and self._agent_card and self._agent_card.url:
            self._agent_card.url = _to_mtls_url(self._agent_card.url)

        logger.info(
            "Orchestrator Agent: Delegating via A2A to '%s' at URL: %s (mTLS=%s)",
            self.name,
            self._agent_card.url if self._agent_card else "unknown",
            mtls_ssl_ctx is not None,
        )

        # Create a fresh httpx.AsyncClient bound to the current active event loop
        # so multi-threaded Agent Engine workers never hit 'Event loop is closed'
        # and never pickle SSLContext/ADC credentials during deployment.
        verify: bool | ssl.SSLContext = (
            mtls_ssl_ctx if mtls_ssl_ctx is not None else True
        )
        async with httpx.AsyncClient(
            auth=GoogleADCAuth(),
            verify=verify,
            timeout=httpx.Timeout(timeout=self._timeout),
        ) as httpx_client:
            self._httpx_client = httpx_client
            self._httpx_client_needs_cleanup = False
            client_config = A2AClientConfig(
                httpx_client=httpx_client,
                streaming=False,
                polling=False,
                supported_transports=[
                    TransportProtocol.jsonrpc,
                    TransportProtocol.http_json,
                ],
            )
            self._a2a_client_factory = A2AClientFactory(config=client_config)
            self._a2a_client = self._a2a_client_factory.create(self._agent_card)
            self._is_resolved = True
            try:
                async for event in super()._run_async_impl(ctx):
                    yield event
            finally:
                self._httpx_client = None
                self._a2a_client = None
                self._a2a_client_factory = None
                self._is_resolved = False


def discover_bookings_a2a_agent(
    project_id: Optional[str] = None,
    location: Optional[str] = None,
    target_display_name: str = "Booking Assistant",
) -> RegistryDiscoveredA2aAgent:
    """Discovers the Bookings agent via Google Cloud Agent Registry and returns a RemoteA2aAgent sub-agent.

    If the Bookings agent is already registered in Agent Registry and reachable, its
    AgentCard is resolved immediately. If not yet reachable (e.g., during package build
    or before initial deployment), resolution is deferred until the first runtime request.
    """
    resolved_project = project_id or os.environ.get("GOOGLE_CLOUD_PROJECT")
    resolved_location = (
        location
        or os.environ.get("LOCATION")
        or os.environ.get("AGENT_REGISTRY_LOCATION", "us-central1")
    )

    eager_discovery = os.environ.get("BOOKINGS_EAGER_DISCOVERY", "false").lower() in (
        "1",
        "true",
        "yes",
    )
    agent_card: Optional[AgentCard] = None
    discovered = False

    if eager_discovery and resolved_project and resolved_location:
        try:
            agent_card = resolve_bookings_agent_card_from_registry(
                project_id=resolved_project,
                location=resolved_location,
                target_display_name=target_display_name,
            )
            discovered = True
        except Exception as exc:
            logger.warning(
                "Deferred Agent Registry discovery for '%s' until runtime: %s",
                target_display_name,
                exc,
            )

    return RegistryDiscoveredA2aAgent(
        name="bookings",
        project_id=resolved_project,
        location=resolved_location,
        target_display_name=target_display_name,
        agent_card=agent_card,
        discovered_from_registry=discovered,
    )
