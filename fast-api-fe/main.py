"""
FastAPI application entry point for the Customer Booking Chatbot frontend.

Serves:
  GET  /                       — Chat UI (Jinja2 HTML)
  POST /v1/chat/completions    — OpenAI-compatible API (proxies to Agent Engine)
  GET  /docs                   — Swagger UI (auto-generated)
"""
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .routers import chat, ui

app = FastAPI(
    title="Customer Booking Chatbot",
    description=(
        "Chat UI + OpenAI-compatible API that proxies to the "
        "customers ADK agent on Vertex AI Agent Engine."
    ),
    version="1.0.0",
)

# Mount static assets (CSS, JS)
_STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")

# Register routers
app.include_router(ui.router)
app.include_router(chat.router)
