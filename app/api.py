"""FastAPI application for the AI Engineering Product Lab."""

from fastapi import FastAPI, HTTPException, status
from fastapi.exceptions import RequestValidationError

from app.config import load_settings
from app.conversation_context import build_contextual_message
from app.database import (
    delete_messages_by_session,
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
    ConversationDeletionResponse,
    ConversationResponse,
    HealthResponse,
    RootResponse,
    StoredMessage,
)

API_VERSION = "0.9.0"
APPLICATION_NAME = "AI Engineering Product Lab"

app = FastAPI(
    title=f"{APPLICATION_NAME} API",
    summary="A practical backend for role-based AI assistants.",
    description=(
        "A learning and product-development API for building "
        "role-based AI assistants, business automation systems, "
        "conversation storage, and WhatsApp-style applications."
    ),
    version=API_VERSION,
    contact={
        "name": "AI WebCo",
    },
    license_info={
        "name": "Learning and portfolio project",
    },
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
    "/",
    response_model=RootResponse,
    status_code=status.HTTP_200_OK,
    tags=["System"],
    summary="Get API information",
)
def root() -> RootResponse:
    """Return basic API information and useful endpoint paths."""
    return RootResponse(
        application=APPLICATION_NAME,
        version=API_VERSION,
        status="running",
        documentation="/docs",
        health="/health",
    )


@app.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    tags=["System"],
    summary="Check application health",
)
def health_check() -> HealthResponse:
    """Return the current application health status."""
    return HealthResponse(
        status="ok",
        application=APPLICATION_NAME,
        version=API_VERSION,
    )


@app.post(
    "/chat",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    tags=["Chat"],
    summary="Generate and store a conversation-aware response",
)
def chat(request: ChatRequest) -> ChatResponse:
    """Generate a response using configurable conversation history."""
    try:
        settings = load_settings()
        provider = create_provider(settings)

        selected_role = normalize_role(request.role)

        previous_messages = get_messages_by_session(
            request.session_id
        )

        contextual_message = build_contextual_message(
            current_message=request.message,
            previous_messages=previous_messages,
            limit=request.history_limit,
        )

        prompt = build_prompt(
            contextual_message,
            selected_role,
        )

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
    tags=["Conversations"],
    summary="Retrieve conversation history",
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


@app.delete(
    "/conversations/{session_id}",
    response_model=ConversationDeletionResponse,
    status_code=status.HTTP_200_OK,
    tags=["Conversations"],
    summary="Delete a stored conversation",
)
def delete_conversation(
    session_id: str,
) -> ConversationDeletionResponse:
    """Delete all stored exchanges belonging to a session."""
    try:
        deleted_count = delete_messages_by_session(session_id)

        if deleted_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation session not found.",
            )

        return ConversationDeletionResponse(
            session_id=session_id,
            deleted_count=deleted_count,
            message="Conversation deleted successfully.",
        )

    except HTTPException:
        raise

    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error