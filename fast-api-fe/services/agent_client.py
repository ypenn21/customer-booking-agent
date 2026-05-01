from google.cloud import aiplatform_v1
from google.protobuf import struct_pb2
from typing import Optional, List, Dict
import asyncio
import logging
import os

import vertexai

logger = logging.getLogger(__name__)

PROJECT_ID = os.environ.get("PROJECT_ID")
LOCATION   = os.environ.get("LOCATION", "us-central1")
ENGINE_ID  = os.environ.get(
    "CUSTOMERS_ENGINE_ID"
)

vertexai.init(project=PROJECT_ID, location=LOCATION)
logger.info("vertexai initialised: project=%s location=%s engine=%s", PROJECT_ID, LOCATION, ENGINE_ID)

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
    user_id: str = "web_user",
    session_id: Optional[str] = None,
    force_new: bool = False,
    iap_token: Optional[str] = None,
    user_timezone: str = "UTC",
) -> tuple[str, str]:
    try:
        grpc_client = get_grpc_client()

        # 1. Handle Metadata (Headers)
        # In gRPC, headers are passed as a list of tuples (key, value)
        # Key MUST be lowercase
        token_str = iap_token
        if isinstance(token_str, bytes):
            token_str = token_str.decode("utf-8")

        metadata = []
        if token_str:
            logger.info("Raw x-user-identity value setting for customer agent: %s", token_str)
            metadata.append(("x-user-identity", token_str))
        if user_timezone:
            metadata.append(("x-user-timezone", user_timezone))

        # 2. Ensure we have a session ID
        if not session_id or force_new:
            session_client = _get_session_client()
            request = aiplatform_v1.CreateSessionRequest(
                parent=ENGINE_ID,
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

        # 3. Prepare the Input Struct
        input_dict = {"message": user_message, "user_id": user_id}
        if session_id:
            input_dict["session_id"] = session_id
        
        # Explicitly pass run_config in the input struct to ensure ADK receives it
        run_config_metadata = {}
        if token_str:
            run_config_metadata["x-user-identity"] = token_str
        if user_timezone:
            run_config_metadata["x-user-timezone"] = user_timezone

        if run_config_metadata:
            input_dict["run_config"] = {
                "custom_metadata": run_config_metadata
            }
        
        input_struct = struct_pb2.Struct()
        input_struct.update(input_dict)

        # 3. Build the Request
        # Note: StreamQueryReasoningEngineRequest uses the reasoning_engine name
        resource_name = ENGINE_ID

        request = aiplatform_v1.StreamQueryReasoningEngineRequest(
            name=resource_name,
            input=input_struct,
        )

        # 4. Call the Service directly via gRPC
        # This bypasses the ADK Runner's 'headers' keyword argument check
        stream = await grpc_client.stream_query_reasoning_engine(
            request=request, 
            metadata=metadata
        )

        final_text = []
        async for response in stream:
            # Navigate the response object
            # In some environments, Reasoning Engine returns HttpBody (with 'data' field)
            # In others, it returns StreamQueryReasoningEngineResponse (with 'output' field)
            if hasattr(response, "data"):
                # Handle HttpBody
                try:
                    chunk_str = response.data.decode("utf-8", errors="ignore")
                    if chunk_str:
                         # ADK usually sends JSON events
                         import json
                         data = json.loads(chunk_str)
                         if "content" in data and "parts" in data["content"]:
                             for part in data["content"]["parts"]:
                                 if "text" in part:
                                     final_text.append(part["text"])
                         elif "text" in data: # Fallback for simpler formats
                             final_text.append(data["text"])
                except Exception as e:
                    logger.warning("Failed to parse HttpBody chunk: %s", e)

            elif hasattr(response, "output") and response.output:
                # Handle StreamQueryReasoningEngineResponse
                output_val = response.output
                if hasattr(output_val, "struct_value"):
                     struct_dict = dict(output_val.struct_value.fields)
                     if "chunks" in struct_dict:
                         for chunk_field in struct_dict["chunks"].list_value.values:
                             chunk = dict(chunk_field.struct_value.fields)
                             if "text" in chunk:
                                 final_text.append(chunk["text"].string_value)
                     elif "content" in struct_dict:
                         content_struct = struct_dict["content"].struct_value
                         if "parts" in content_struct.fields:
                             for part_field in content_struct.fields["parts"].list_value.values:
                                 part = part_field.struct_value.fields
                                 if "text" in part:
                                     final_text.append(part["text"].string_value)
                elif hasattr(output_val, "string_value"):
                     final_text.append(output_val.string_value)
        
        return "".join(final_text), session_id or "new_session"

    except Exception as e:
        logger.exception("gRPC query_agent failed")
        return f"Error communicating with agent: {e}", session_id or ""

def _get_session_client():
    # We can use a sync client for some or async for all.
    # Let's use async for consistency with query_agent.
    return aiplatform_v1.SessionServiceAsyncClient(client_options=client_options)

async def list_user_sessions(user_id: str) -> list[dict]:
    """
    List all sessions started by a user.
    """
    try:
        if not ENGINE_ID:
            return []
        
        client = _get_session_client()
        # parent should be the reasoning engine resource name
        parent = ENGINE_ID 
        
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
        client = _get_session_client()
        session_name = f"{ENGINE_ID}/sessions/{session_id}"
        
        request = aiplatform_v1.ListEventsRequest(parent=session_name)
        pager = await client.list_events(request=request)
        
        messages = []
        async for event in pager:
            if hasattr(event, "content") and event.content.parts:
                role = getattr(event.content, "role", getattr(event, "author", "unknown"))
                
                # Combine all text parts; ignore function call parts (which have no 'text' or empty text)
                text_parts = [p.text for p in event.content.parts if hasattr(p, "text") and p.text]
                if text_parts:
                    messages.append({
                        "role": role,
                        "content": "\n".join(text_parts)
                    })
        return messages
    except Exception as e:
        logger.exception(f"get_session_history failed for session {session_id}")
        return []

