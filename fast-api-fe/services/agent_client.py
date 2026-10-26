from google.cloud import aiplatform_v1
from google.protobuf import struct_pb2
from typing import Any, Optional, List, Dict
import asyncio
import json
import logging
import os
import re
import vertexai
from vertexai import agent_engines
from google.adk.integrations.agent_registry import AgentRegistry

logger = logging.getLogger(__name__)

PROJECT_ID = os.environ.get("PROJECT_ID") or os.environ.get("GOOGLE_CLOUD_PROJECT")
LOCATION   = os.environ.get("LOCATION", "us-central1")
AGENT_REGISTRY_LOCATION = os.environ.get("AGENT_REGISTRY_LOCATION", LOCATION)
ORCHESTRATOR_AGENT_DISPLAY_NAME = os.environ.get(
    "ORCHESTRATOR_AGENT_DISPLAY_NAME", "Orchestrator Agent"
)

# Optional static override (used only if explicitly set in env; otherwise resolved via Agent Registry)
ENGINE_ID: Optional[str] = os.environ.get("ORCHESTRATOR_ENGINE_ID") or None
_RESOLVED_ENGINE_ID: Optional[str] = None

_REASONING_ENGINE_PATTERN = re.compile(
    r"(projects/[^/]+/locations/[^/]+/reasoningEngines/[^/:?\s]+)"
)
_URN_REASONING_ENGINE_PATTERN = re.compile(
    r"projects:([^:]+):locations:([^:]+):aiplatform:reasoningEngines:([^:\s]+)"
)


def _extract_reasoning_engine_id_from_agent_entry(
    entry: Dict[str, Any],
) -> Optional[str]:
    """Extracts the canonical Reasoning Engine resource name from an Agent Registry entry."""
    # 1. Primary: attributes['agentregistry.googleapis.com/system/RuntimeReference']['uri']
    # Format: "//aiplatform.googleapis.com/projects/48196429354/locations/us-central1/reasoningEngines/1818476233864773632"
    attributes = entry.get("attributes") or {}
    runtime_ref = attributes.get(
        "agentregistry.googleapis.com/system/RuntimeReference"
    )
    if isinstance(runtime_ref, dict):
        uri = runtime_ref.get("uri", "")
        match = _REASONING_ENGINE_PATTERN.search(uri)
        if match:
            return match.group(1)

    # 2. Fallback 1: protocols[].interfaces[].url
    # Format: "https://us-central1-aiplatform.googleapis.com/v1/projects/.../reasoningEngines/...:streamQuery"
    for protocol in entry.get("protocols") or []:
        for iface in protocol.get("interfaces") or []:
            url = iface.get("url", "")
            match = _REASONING_ENGINE_PATTERN.search(url)
            if match:
                return match.group(1)

    # 3. Fallback 2: card.content.url (if exposed as A2A card)
    card_url = (entry.get("card") or {}).get("content", {}).get("url", "")
    if card_url:
        match = _REASONING_ENGINE_PATTERN.search(card_url)
        if match:
            return match.group(1)

    # 4. Fallback 3: agentId URN
    # Format: "urn:agent:projects-48196429354:projects:48196429354:locations:us-central1:aiplatform:reasoningEngines:1818476233864773632"
    agent_id_urn = entry.get("agentId", "")
    urn_match = _URN_REASONING_ENGINE_PATTERN.search(agent_id_urn)
    if urn_match:
        proj, loc, eng_id = urn_match.groups()
        return f"projects/{proj}/locations/{loc}/reasoningEngines/{eng_id}"

    return None


def resolve_orchestrator_engine_id(
    project_id: Optional[str] = None,
    location: Optional[str] = None,
    target_display_name: Optional[str] = None,
) -> str:
    """Queries Google Cloud Agent Registry to discover the Orchestrator Reasoning Engine resource name."""
    resolved_project = project_id or PROJECT_ID
    resolved_location = location or AGENT_REGISTRY_LOCATION
    resolved_target = target_display_name or ORCHESTRATOR_AGENT_DISPLAY_NAME

    if not resolved_project:
        raise RuntimeError(
            "PROJECT_ID must be set to discover the Orchestrator Agent in Agent Registry."
        )

    registry = AgentRegistry(
        project_id=resolved_project,
        location=resolved_location,
    )

    agent_registry_name = os.environ.get("ORCHESTRATOR_AGENT_REGISTRY_NAME")
    matched_entry: Optional[Dict[str, Any]] = None

    if agent_registry_name:
        matched_entry = registry.get_agent_info(agent_registry_name)
    else:
        filter_str = os.environ.get("ORCHESTRATOR_REGISTRY_FILTER")
        response = registry.list_agents(filter_str=filter_str)
        agents = response.get("agents", [])

        # Prefer exact case-insensitive displayName match first, then substring match
        for entry in agents:
            display_name = entry.get("displayName", "")
            if display_name.lower() == resolved_target.lower():
                matched_entry = entry
                break

        if not matched_entry:
            for entry in agents:
                display_name = entry.get("displayName", "")
                if (
                    resolved_target.lower() in display_name.lower()
                    or "orchestrator" in display_name.lower()
                ):
                    matched_entry = entry
                    break

        if not matched_entry:
            raise RuntimeError(
                f"Could not discover '{resolved_target}' in Agent Registry "
                f"(project={resolved_project}, location={resolved_location}). "
                f"Found agents: {[a.get('displayName') for a in agents]}"
            )

    engine_id = _extract_reasoning_engine_id_from_agent_entry(matched_entry)
    if not engine_id:
        raise RuntimeError(
            f"Discovered Agent Registry entry '{matched_entry.get('name')}' "
            f"(displayName='{matched_entry.get('displayName')}'), but could not extract "
            "a Reasoning Engine resource ID from its metadata."
        )

    logger.info(
        "Discovered Orchestrator Agent in Agent Registry: registry_name=%s display_name=%s engine_id=%s",
        matched_entry.get("name"),
        matched_entry.get("displayName"),
        engine_id,
    )
    return engine_id


def get_orchestrator_engine_id(force_refresh: bool = False) -> str:
    """Returns the cached Orchestrator Reasoning Engine ID, discovering it via Agent Registry if needed."""
    global _RESOLVED_ENGINE_ID
    if ENGINE_ID and not force_refresh:
        return ENGINE_ID
    if _RESOLVED_ENGINE_ID and not force_refresh:
        return _RESOLVED_ENGINE_ID

    _RESOLVED_ENGINE_ID = resolve_orchestrator_engine_id()
    return _RESOLVED_ENGINE_ID


if PROJECT_ID:
    vertexai.init(project=PROJECT_ID, location=LOCATION)
logger.info(
    "vertexai initialised: project=%s location=%s static_engine_override=%s",
    PROJECT_ID,
    LOCATION,
    ENGINE_ID,
)

# Initialize the low-level client once
api_endpoint = f"{LOCATION}-aiplatform.googleapis.com"
client_options = {"api_endpoint": api_endpoint}
_GRPC_CLIENT = None

def get_grpc_client():
    global _GRPC_CLIENT
    if _GRPC_CLIENT is None:
        _GRPC_CLIENT = aiplatform_v1.ReasoningEngineExecutionServiceAsyncClient(client_options=client_options)
    return _GRPC_CLIENT

async def query_agent(
    user_message: str,
    user_id: str,
    session_id: Optional[str] = None,
    force_new: bool = False,
    iap_token: Optional[str] = None,
    user_timezone: str = "UTC",
) -> tuple[str, str]:
    try:
        engine_id = get_orchestrator_engine_id()

        # 1. Handle Metadata (Headers)
        token_str = iap_token
        if isinstance(token_str, bytes):
            token_str = token_str.decode("utf-8")

        metadata = []
        if token_str:
            logger.info("Raw x-user-identity value setting for orchestrator agent: %s", token_str)
            metadata.append(("x-user-identity", token_str))
        if user_timezone:
            metadata.append(("x-user-timezone", user_timezone))

        # 2. Ensure we have a session ID
        session_client = _get_session_client()
        if not session_id or force_new:
            request = aiplatform_v1.CreateSessionRequest(
                parent=engine_id,
                session=aiplatform_v1.Session(user_id=user_id)
            )
            # Pass metadata to create_session so the agent receives the identity header
            operation = await session_client.create_session(request=request, metadata=metadata)
            if hasattr(operation, "result"):
                 session_obj = await operation.result()
            else:
                 session_obj = operation
            
            session_id = session_obj.name.split("/")[-1]
            logger.info("Created new session: %s", session_id)
        else:
            # Verify ownership to prevent IDOR
            session_name = f"{engine_id}/sessions/{session_id}"
            session = await session_client.get_session(name=session_name)
            if getattr(session, "user_id", None) != user_id:
                 logger.warning("Unauthorized query access: user=%s session=%s", user_id, session_id)
                 return "Error: Unauthorized session access.", session_id

        # 3. Connect to Remote Agent Engine via SDK
        remote_app = agent_engines.get(engine_id)

        run_config_metadata = {}
        if token_str:
            run_config_metadata["x-user-identity"] = token_str
        if user_timezone:
            run_config_metadata["x-user-timezone"] = user_timezone

        run_config = {"custom_metadata": run_config_metadata} if run_config_metadata else None

        # 4. Stream query using stream_query
        response_stream = remote_app.stream_query(
            message=user_message,
            user_id=user_id,
            session_id=session_id,
            run_config=run_config,
        )

        agent_reply = _consume_response_stream(response_stream)
        return agent_reply, session_id or "new_session"

    except Exception as e:
        logger.exception("query_agent failed")
        msg = str(e)
        if "Blocked by Model Armor" in msg or "violated Prompt Injection" in msg or "Jailbreak" in msg:
            return msg, session_id or ""
        return f"Error communicating with agent: {e}", session_id or ""

def _get_session_client():
    # We can use a sync client for some or async for all.
    # Let's use async for consistency with query_agent.
    return aiplatform_v1.SessionServiceAsyncClient(client_options=client_options)

def _extract_text_from_part(part) -> Optional[str]:
    """Extracts user-visible text from a content part, including request_user_input calls."""
    if isinstance(part, dict):
        if part.get("thought"):
            return None
        text = part.get("text")
        if text:
            return text
        fc = part.get("function_call") or part.get("functionCall")
        if isinstance(fc, dict) and fc.get("name") == "request_user_input":
            args = fc.get("args") or {}
            if isinstance(args, dict):
                msg = args.get("message")
                if msg:
                    return str(msg)
    else:
        if getattr(part, "thought", False):
            return None
        text = getattr(part, "text", None)
        if text:
            return text
        fc = getattr(part, "function_call", None)
        if fc and getattr(fc, "name", None) == "request_user_input":
            args = getattr(fc, "args", None)
            if args is not None and hasattr(args, "get"):
                msg = args.get("message")
                if msg:
                    return str(msg)
    return None


def _extract_error_from_event(event) -> Optional[str]:
    """Extracts error message from an event (e.g. Model Armor floor setting or API error)."""
    if not event:
        return None

    # Handle dict-like event
    if isinstance(event, dict):
        err = event.get("error")
        if isinstance(err, dict):
            msg = err.get("errorMessage") or err.get("error_message") or err.get("message")
            if msg:
                return str(msg)
            code = err.get("errorCode") or err.get("code")
            if code is not None and str(code).lower() not in ("undefined", "none", ""):
                return f"Error code: {code}"
        elif isinstance(err, str) and err.strip():
            return err.strip()

        for k in ("errorMessage", "error_message", "message"):
            val = event.get(k)
            if val and any(s in str(val).lower() for s in ["blocked", "armor", "violated", "error", "filter"]):
                return str(val)

    # Handle object-like event (Protobuf / SDK class / ADK Event)
    err = getattr(event, "error", None)
    if err:
        if isinstance(err, dict):
            msg = err.get("errorMessage") or err.get("error_message") or err.get("message")
            if msg:
                return str(msg)
        elif isinstance(err, str) and err.strip():
            return err.strip()
        else:
            for attr in ("errorMessage", "error_message", "message"):
                msg = getattr(err, attr, None)
                if msg:
                    return str(msg)

    for attr in ("errorMessage", "error_message", "message"):
        val = getattr(event, attr, None)
        if val:
            return str(val)

    # Check raw_event if present
    raw = getattr(event, "raw_event", None)
    if raw:
        if hasattr(raw, "items"):
            return _extract_error_from_event(dict(raw))
        elif hasattr(raw, "__dict__"):
            return _extract_error_from_event(raw.__dict__)

    return None


def _consume_response_stream(response_stream) -> str:
    """Helper to consolidate text from an ADK response stream."""
    final_text = []
    error_messages = []
    for event in response_stream:
        # Check for error in event (e.g. Model Armor block)
        err = _extract_error_from_event(event)
        if err and err not in error_messages:
            logger.warning("Error event detected in response stream: %s", err)
            error_messages.append(err)

        # ADK stream events can be dicts (common in remote calls) or objects
        if isinstance(event, dict):
            content = event.get("content", {})
            role = event.get("role") or content.get("role")
            if role == "model" or not role:
                for part in content.get("parts", []):
                    extracted = _extract_text_from_part(part)
                    if extracted and extracted not in final_text:
                        final_text.append(extracted)
                if "text" in event and event["text"] and event["text"] not in final_text:
                    final_text.append(event["text"])
        elif hasattr(event, "content"):
            content = event.content
            role = getattr(content, "role", getattr(event, "role", None))
            if role == "model" or not role:
                if hasattr(content, "parts"):
                    for part in content.parts:
                        extracted = _extract_text_from_part(part)
                        if extracted and extracted not in final_text:
                            final_text.append(extracted)

    if error_messages:
        err_str = "\n".join(error_messages)
        if not final_text:
            return err_str
        return f"{''.join(final_text)}\n\n⚠️ {err_str}"

    return "".join(final_text)

async def list_user_sessions(user_id: str) -> list[dict]:
    """
    List all sessions started by a user.
    """
    try:
        engine_id = get_orchestrator_engine_id()
        if not engine_id:
            return []
        
        client = _get_session_client()
        # parent should be the reasoning engine resource name
        parent = engine_id 
        
        # filter by user_id if supported by the API
        request = aiplatform_v1.ListSessionsRequest(
            parent=parent,
            filter=f'user_id="{user_id}"'
        )
        
        pager = await client.list_sessions(request=request)
        sessions = []
        async for s in pager:
            sessions.append({"id": s.name.split("/")[-1], "user_id": getattr(s, "user_id", "unknown")})
        return sessions
    except Exception as e:
        logger.exception("list_user_sessions failed")
        return []

async def get_session_history(user_id: str, session_id: str) -> list[dict]:
    """Retrieves the message history for a given session."""
    try:
        engine_id = get_orchestrator_engine_id()
        if not engine_id:
            return []
            
        client = _get_session_client()
        session_name = f"{engine_id}/sessions/{session_id}"
        
        # Verify ownership to prevent IDOR
        session = await client.get_session(name=session_name)
        if getattr(session, "user_id", None) != user_id:
            logger.warning(
                "Unauthorized history access: user=%s session=%s owner=%s",
                user_id, session_id, getattr(session, "user_id", "unknown")
            )
            return []
        
        request = aiplatform_v1.ListEventsRequest(parent=session_name)
        pager = await client.list_events(request=request)
        
        messages = []
        async for event in pager:
            # Check for error event first (e.g. Model Armor block or system error)
            err = _extract_error_from_event(event)
            if err:
                messages.append({
                    "role": "assistant",
                    "content": err,
                })
                continue

            if hasattr(event, "content") and event.content.parts:
                role = getattr(event.content, "role", getattr(event, "author", "unknown"))
                
                # Combine all text parts and request_user_input prompts
                text_parts = []
                for p in event.content.parts:
                    extracted = _extract_text_from_part(p)
                    if extracted and extracted not in text_parts:
                        text_parts.append(extracted)
                if text_parts:
                    messages.append({
                        "role": role,
                        "content": "\n".join(text_parts)
                    })
        return messages
    except Exception as e:
        logger.exception(f"get_session_history failed for session {session_id}")
        return []

