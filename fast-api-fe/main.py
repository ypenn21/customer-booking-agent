"""
FastAPI application entry point for the Customer Booking Chatbot frontend.

Serves:
  GET  /                        — Chat UI (Jinja2 HTML via ui.router)
  POST /v1/chat/completions    — OpenAI-compatible API (via chat.router)
  GET  /auth/handler.html      — Auth helper for Google identity
  GET  /docs                   — Swagger UI (auto-generated)
"""
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

# Ensure relative imports work by running as a module: 
# python -m your_package_name.main
from .routers import chat, ui

app = FastAPI(
    title="Customer Booking Chatbot",
    description=(
        "Chat UI + OpenAI-compatible API that proxies to the "
        "customers ADK agent on Vertex AI Agent Engine."
    ),
    version="1.0.0",
)

import logging

# Set the root logger to INFO and format the output
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Configuration
BASE_DIR = Path(__file__).resolve().parent

# Mount static assets (CSS, JS)
# We use resolve() to ensure the path is absolute and valid
_STATIC_DIR = BASE_DIR / "static"

if _STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")
else:
    print(f"Warning: Static directory not found at {_STATIC_DIR}. Skipping mount.")

# Register routers
# These define the / and /v1/chat/completions logic
app.include_router(ui.router)
app.include_router(chat.router)

