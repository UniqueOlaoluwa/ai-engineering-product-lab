"""FastAPI application for the AI Engineering Product Lab."""

from fastapi import FastAPI, HTTPException, status
from fastapi.exceptions import RequestValidationError

from app.config import load_settings
from app.database import (
    get_messages_by_session,
    initialize_database,
    save_message,
)
from app.error_handlers import (
    http_exception_handler,
    validation_exception_handler,
)
from app.exceptions import PromptTemplateError, ProviderError
from app.middleware import request_logging_middleware
from app.prompt_builder import build_prompt, get_role_name, normalize_role
from app.providers.factory import create_provider
from app.schemas import (
    ChatRequest,
    ChatResponse,
    ConversationResponse,
    HealthResponse,
    StoredMessage,
)

API_VERSION = "0.5.0"

app = FastAPI(
    title="AI Engineering Product Lab API",
    description=(
        "A learning API for building practical AI assistants, "
        "business automation systems, and WhatsApp-style applications."
    ),
    version=API_VERSION,
)

app.middleware("http")(request_logging_middleware)

app.add_exception_handler(
    HTTPException,
    http_exception_handler,
)

app.add_exception_handler(
    RequestValidationError,
    validation_exception_handler,
)

initialize_database()


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
    """Build a prompt, generate a response, and save the conversation."""
    try:
        settings = load_settings()
        provider = create_provider(settings)

        selected_role = normalize_role(request.role)
        prompt = build_prompt(request.message, selected_role)
        reply = provider.generate(prompt)
        provider_name = type(provider).__name__

        message_id = save_message(
            session_id=request.session_id,
            role=selected_role,
            user_message=request.message,
            assistant_reply=reply,
            provider=provider_name,
        )

        return ChatResponse(
            message_id=message_id,
            session_id=request.session_id,
            role=selected_role,
            role_name=get_role_name(selected_role),
            reply=reply,
            provider=provider_name,
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


@app.get(
    "/conversations/{session_id}",
    response_model=ConversationResponse,
    status_code=status.HTTP_200_OK,
)
def get_conversation(session_id: str) -> ConversationResponse:
    """Return all stored chatbot exchanges for a session."""
    try:
        messages = get_messages_by_session(session_id)

        if not messages:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation session not found.",
            )

        stored_messages = [
            StoredMessage(
                id=message["id"],
                role=message["role"],
                user_message=message["user_message"],
                assistant_reply=message["assistant_reply"],
                provider=message["provider"],
                created_at=message["created_at"],
            )
            for message in messages
        ]

        return ConversationResponse(
            session_id=session_id,
            message_count=len(stored_messages),
            messages=stored_messages,
        )

    except HTTPException:
        raise

    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error