"""FastAPI application for the AI Engineering Product Lab."""

import json
from json import JSONDecodeError

from fastapi import (
    FastAPI,
    Header,
    HTTPException,
    Query,
    Request,
    status,
)
from fastapi.exceptions import RequestValidationError
from fastapi.responses import PlainTextResponse
from pydantic import ValidationError

from app.chat_service import process_chat_message
from app.database import (
    DEFAULT_CONVERSATION_LIMIT,
    MAX_CONVERSATION_LIMIT,
    MAX_CONVERSATION_SEARCH_LENGTH,
    count_conversation_sessions,
    delete_messages_by_session,
    initialize_database,
    list_conversation_sessions,
)
from app.error_handlers import (
    http_exception_handler,
    validation_exception_handler,
)
from app.exceptions import PromptTemplateError, ProviderError
from app.message_pagination import (
    DEFAULT_MESSAGE_LIMIT,
    MAX_MESSAGE_LIMIT,
    count_messages_by_session,
    get_messages_by_session_page,
)
from app.middleware import request_logging_middleware
from app.schemas import (
    ChatRequest,
    ChatResponse,
    ConversationDeletionResponse,
    ConversationListResponse,
    ConversationResponse,
    ConversationSummary,
    HealthResponse,
    RootResponse,
    StoredMessage,
    WhatsAppWebhookRequest,
    WhatsAppWebhookResponse,
)
from app.webhook_events import (
    get_webhook_event,
    initialize_webhook_events_table,
    save_webhook_event,
)
from app.whatsapp import build_whatsapp_session_id
from app.whatsapp_signature import (
    WhatsAppSignatureConfigurationError,
    WhatsAppSignatureError,
    get_configured_meta_app_secret,
    verify_whatsapp_signature,
)
from app.whatsapp_verification import (
    WhatsAppVerificationConfigurationError,
    WhatsAppVerificationError,
    get_configured_whatsapp_verify_token,
    verify_whatsapp_webhook,
)

API_VERSION = "0.15.0"
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
initialize_webhook_events_table()


def process_whatsapp_request(
    request: WhatsAppWebhookRequest,
) -> WhatsAppWebhookResponse:
    """Process one validated WhatsApp-style request idempotently."""
    existing_event = get_webhook_event(
        provider="whatsapp",
        inbound_message_id=request.message_id,
    )

    if existing_event is not None:
        return WhatsAppWebhookResponse(
            status="duplicate",
            inbound_message_id=request.message_id,
            session_id=existing_event["session_id"],
            sender_phone=request.sender_phone,
            reply=existing_event["reply"],
            provider=existing_event["response_provider"],
            stored_message_id=existing_event[
                "stored_message_id"
            ],
        )

    session_id = build_whatsapp_session_id(
        request.sender_phone
    )

    result = process_chat_message(
        message=request.message,
        role=request.role,
        session_id=session_id,
        history_limit=request.history_limit,
    )

    save_webhook_event(
        provider="whatsapp",
        inbound_message_id=request.message_id,
        session_id=result.session_id,
        stored_message_id=result.message_id,
        reply=result.reply,
        response_provider=result.provider,
    )

    return WhatsAppWebhookResponse(
        status="processed",
        inbound_message_id=request.message_id,
        session_id=result.session_id,
        sender_phone=request.sender_phone,
        reply=result.reply,
        provider=result.provider,
        stored_message_id=result.message_id,
    )


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
    """Process a chatbot message through the reusable service."""
    try:
        result = process_chat_message(
            message=request.message,
            role=request.role,
            session_id=request.session_id,
            history_limit=request.history_limit,
        )

        return ChatResponse(
            message_id=result.message_id,
            session_id=result.session_id,
            role=result.role,
            role_name=result.role_name,
            reply=result.reply,
            provider=result.provider,
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
    "/webhooks/whatsapp",
    response_class=PlainTextResponse,
    status_code=status.HTTP_200_OK,
    tags=["WhatsApp"],
    summary="Verify a WhatsApp webhook subscription",
)
def verify_whatsapp_webhook_endpoint(
    mode: str | None = Query(
        default=None,
        alias="hub.mode",
        description="Webhook subscription mode.",
    ),
    verify_token: str | None = Query(
        default=None,
        alias="hub.verify_token",
        description="Incoming verification token.",
    ),
    challenge: str | None = Query(
        default=None,
        alias="hub.challenge",
        description="Challenge returned after successful verification.",
    ),
) -> PlainTextResponse:
    """Validate a WhatsApp webhook-verification request."""
    try:
        expected_token = (
            get_configured_whatsapp_verify_token()
        )

        verified_challenge = verify_whatsapp_webhook(
            mode=mode,
            verify_token=verify_token,
            challenge=challenge,
            expected_token=expected_token,
        )

        return PlainTextResponse(
            content=verified_challenge,
            status_code=status.HTTP_200_OK,
        )

    except WhatsAppVerificationConfigurationError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(error),
        ) from error

    except WhatsAppVerificationError as error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(error),
        ) from error


@app.post(
    "/webhooks/whatsapp/mock",
    response_model=WhatsAppWebhookResponse,
    status_code=status.HTTP_200_OK,
    tags=["WhatsApp"],
    summary="Process a mock incoming WhatsApp message",
)
def mock_whatsapp_webhook(
    request: WhatsAppWebhookRequest,
) -> WhatsAppWebhookResponse:
    """Process an unsigned local-development WhatsApp message."""
    try:
        return process_whatsapp_request(request)

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


@app.post(
    "/webhooks/whatsapp/signed",
    response_model=WhatsAppWebhookResponse,
    status_code=status.HTTP_200_OK,
    tags=["WhatsApp"],
    summary="Process a signature-authenticated WhatsApp message",
)
async def signed_whatsapp_webhook(
    request: Request,
    signature_header: str | None = Header(
        default=None,
        alias="X-Hub-Signature-256",
        description="HMAC-SHA256 signature of the raw request body.",
    ),
) -> WhatsAppWebhookResponse:
    """Authenticate raw request bytes before parsing the payload."""
    raw_payload = await request.body()

    try:
        app_secret = get_configured_meta_app_secret()

        verify_whatsapp_signature(
            payload=raw_payload,
            signature_header=signature_header,
            app_secret=app_secret,
        )

        try:
            decoded_payload = json.loads(raw_payload)
        except (
            JSONDecodeError,
            UnicodeDecodeError,
        ) as error:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Webhook payload must be valid JSON.",
            ) from error

        try:
            validated_payload = (
                WhatsAppWebhookRequest.model_validate(
                    decoded_payload
                )
            )
        except ValidationError as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Webhook payload validation failed.",
            ) from error

        return process_whatsapp_request(
            validated_payload
        )

    except HTTPException:
        raise

    except WhatsAppSignatureConfigurationError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(error),
        ) from error

    except WhatsAppSignatureError as error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(error),
        ) from error

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
    "/conversations",
    response_model=ConversationListResponse,
    status_code=status.HTTP_200_OK,
    tags=["Conversations"],
    summary="List and search stored conversations",
)
def list_conversations(
    limit: int = Query(
        default=DEFAULT_CONVERSATION_LIMIT,
        ge=1,
        le=MAX_CONVERSATION_LIMIT,
        description="Maximum number of conversations to return.",
    ),
    offset: int = Query(
        default=0,
        ge=0,
        description="Number of conversation summaries to skip.",
    ),
    search: str | None = Query(
        default=None,
        min_length=1,
        max_length=MAX_CONVERSATION_SEARCH_LENGTH,
        pattern=r".*\S.*",
        description=(
            "Optional case-insensitive partial search applied "
            "to conversation session IDs."
        ),
        examples=["clinic"],
    ),
) -> ConversationListResponse:
    """Return paginated and optionally filtered conversations."""
    try:
        total = count_conversation_sessions(
            search=search,
        )

        conversations = list_conversation_sessions(
            limit=limit,
            offset=offset,
            search=search,
        )

        summaries = [
            ConversationSummary(
                session_id=conversation["session_id"],
                message_count=conversation["message_count"],
                first_created_at=conversation["first_created_at"],
                last_created_at=conversation["last_created_at"],
            )
            for conversation in conversations
        ]

        return ConversationListResponse(
            total=total,
            limit=limit,
            offset=offset,
            conversations=summaries,
        )

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
    summary="Retrieve paginated conversation history",
)
def get_conversation(
    session_id: str,
    limit: int = Query(
        default=DEFAULT_MESSAGE_LIMIT,
        ge=1,
        le=MAX_MESSAGE_LIMIT,
        description="Maximum number of messages to return.",
    ),
    offset: int = Query(
        default=0,
        ge=0,
        description="Number of stored messages to skip.",
    ),
) -> ConversationResponse:
    """Return one paginated page of exchanges for a session."""
    try:
        total = count_messages_by_session(session_id)

        if total == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation session not found.",
            )

        messages = get_messages_by_session_page(
            session_id=session_id,
            limit=limit,
            offset=offset,
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
            total=total,
            limit=limit,
            offset=offset,
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