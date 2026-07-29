"""FastAPI application for the AI Engineering Product Lab."""

from fastapi import FastAPI, HTTPException, status

from app.config import load_settings
from app.exceptions import PromptTemplateError, ProviderError
from app.prompt_builder import build_prompt, get_role_name, normalize_role
from app.providers.factory import create_provider
from app.schemas import ChatRequest, ChatResponse, HealthResponse

API_VERSION = "0.3.0"

app = FastAPI(
    title="AI Engineering Product Lab API",
    description=(
        "A learning API for building practical AI assistants, "
        "business automation systems, and WhatsApp-style applications."
    ),
    version=API_VERSION,
)


@app.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
)
def health_check() -> HealthResponse:
    """Return the current application health status."""
    return HealthResponse(
        status="ok",
        application="AI Engineering Product Lab",
        version=API_VERSION,
    )


@app.post(
    "/chat",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
)
def chat(request: ChatRequest) -> ChatResponse:
    """Build a role-based prompt and return a provider response."""
    try:
        settings = load_settings()
        provider = create_provider(settings)

        selected_role = normalize_role(request.role)
        prompt = build_prompt(request.message, selected_role)
        reply = provider.generate(prompt)

        return ChatResponse(
            role=selected_role,
            role_name=get_role_name(selected_role),
            reply=reply,
            provider=type(provider).__name__,
        )
    except PromptTemplateError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Prompt configuration error: {error}",
        ) from error
    except ProviderError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"AI provider error: {error}",
        ) from error
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error