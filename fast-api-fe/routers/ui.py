"""
UI router: serves the Jinja2-rendered chat HTML page.
"""
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter(tags=["UI"])

# Resolve templates directory relative to this file so it works
# whether the app is run from the project root or fast-api-fe/
_TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def chat_ui(request: Request) -> HTMLResponse:
    """Render the chat UI."""
    return templates.TemplateResponse(
        request=request,
        name="chat.html",
        context={"title": "Customer Booking Assistant"},
    )
