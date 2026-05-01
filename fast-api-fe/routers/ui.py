"""
UI router: serves the Jinja2-rendered chat HTML page.
"""
import os
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter(tags=["UI"])

# Configuration
PROJECT_ID = os.environ.get("PROJECT_ID")

# Resolve templates directory relative to this file so it works
# whether the app is run from the project root or fast-api-fe/
_BASE_DIR = Path(__file__).resolve().parent.parent
_TEMPLATES_DIR = _BASE_DIR / "templates"
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def chat_ui(request: Request) -> HTMLResponse:
    """Render the chat UI."""
    return templates.TemplateResponse(
        request=request,
        name="chat.html",
        context={"title": "Customer Booking Assistant"},
    )


@router.get("/auth/handler.html", response_class=HTMLResponse)
def auth_handler():
    """
    Serves the auth handler HTML file, injecting the current Project ID.
    """
    handler_path = _BASE_DIR / "handler.html"

    try:
        with open(handler_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Inject the project ID into the template placeholder
        rendered_content = content.replace("{{project_id}}", PROJECT_ID)
        return HTMLResponse(content=rendered_content)

    except FileNotFoundError:
        return HTMLResponse(
            content=f"<html><body>Error: handler.html not found at {handler_path}</body></html>",
            status_code=404,
        )
