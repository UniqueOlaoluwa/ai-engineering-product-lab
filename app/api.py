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
from fastapi.responses import JSONResponse, PlainTextResponse
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
from app.meta_whatsapp_parser import (
    MetaWhatsAppNoMessageError,
    MetaWhatsAppPayloadError,
    parse_meta_whatsapp_batch,
)
from app.middleware import request_logging_middleware
from app.outbound_deliveries import (
    DEFAULT_RETRY_LIMIT,
    MAX_RETRY_LIMIT,
    OutboundDeliveryStorageError,
    initialize_outbound_deliveries_table,
    list_retry_pending_deliveries,
)
from app.outbound_delivery_service import (
    OutboundDeliveryAttemptResult,
    persist_and_deliver_reply,
)
from app.outbound_retry_service import (
    OutboundDeliveryRetryError,
    OutboundRetryResult,
    retry_outbound_delivery,
    retry_pending_deliveries,
)
from app.schemas import (
    ChatRequest,
    ChatResponse,
    ConversationDeletionResponse,
    ConversationListResponse,
    ConversationResponse,
    ConversationSummary,
    HealthResponse,
    MetaWhatsAppBatchItemResponse,
    MetaWhatsAppBatchResponse,
    OutboundDeliveryRecordResponse,
    OutboundRetryBatchResponse,
    OutboundRetryItemResponse,
    RetryPendingDeliveryListResponse,
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

API_VERSION = "0.18.0"
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
initialize_outbound_deliveries_table()


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


def decode_json_payload(
    raw_payload: bytes,
) -> object:
    """Decode raw webhook bytes into a JSON-compatible value."""
    try:
        return json.loads(raw_payload)
    except (
        JSONDecodeError,
        UnicodeDecodeError,
    ) as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Webhook payload must be valid JSON.",
        ) from error


def authenticate_whatsapp_payload(
    raw_payload: bytes,
    signature_header: str | None,
) -> None:
    """Authenticate exact webhook bytes using the Meta app secret."""
    app_secret = get_configured_meta_app_secret()

    verify_whatsapp_signature(
        payload=raw_payload,
        signature_header=signature_header,
        app_secret=app_secret,
    )


def build_persisted_delivery_item(
    processing_result: WhatsAppWebhookResponse,
    delivery_result: OutboundDeliveryAttemptResult | None,
) -> MetaWhatsAppBatchItemResponse:
    """Combine processing and persisted-delivery outcomes."""
    if delivery_result is None:
        return MetaWhatsAppBatchItemResponse(
            status=processing_result.status,
            inbound_message_id=(
                processing_result.inbound_message_id
            ),
            sender_phone=processing_result.sender_phone,
            session_id=processing_result.session_id,
            reply=processing_result.reply,
            provider=processing_result.provider,
            stored_message_id=(
                processing_result.stored_message_id
            ),
            delivery_status="skipped",
        )

    return MetaWhatsAppBatchItemResponse(
        status=processing_result.status,
        inbound_message_id=(
            processing_result.inbound_message_id
        ),
        sender_phone=processing_result.sender_phone,
        session_id=processing_result.session_id,
        reply=processing_result.reply,
        provider=processing_result.provider,
        stored_message_id=processing_result.stored_message_id,
        delivery_status=delivery_result.status,
        delivery_provider=(
            delivery_result.delivery_provider
        ),
        outbound_message_id=(
            delivery_result.outbound_message_id
        ),
        delivery_error=delivery_result.error,
        delivery_attempt_count=(
            delivery_result.attempt_count
        ),
    )


def build_retry_item_response(
    result: OutboundRetryResult,
) -> OutboundRetryItemResponse:
    """Convert one retry-service result into an API model."""
    return OutboundRetryItemResponse(
        status=result.status,
        inbound_message_id=result.inbound_message_id,
        recipient_phone=result.recipient_phone,
        message=result.message,
        attempt_count=result.attempt_count,
        delivery_provider=result.delivery_provider,
        outbound_message_id=result.outbound_message_id,
        error=result.error,
    )


@app.get(
    "/",
    response_model=RootResponse,
    status_code=status.HTTP_200_OK,
    tags=["System"],
)
def root() -> RootResponse:
    """Return basic API information."""
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
)
def chat(
    request: ChatRequest,
) -> ChatResponse:
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
)
def verify_whatsapp_webhook_endpoint(
    mode: str | None = Query(
        default=None,
        alias="hub.mode",
    ),
    verify_token: str | None = Query(
        default=None,
        alias="hub.verify_token",
    ),
    challenge: str | None = Query(
        default=None,
        alias="hub.challenge",
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
)
async def signed_whatsapp_webhook(
    request: Request,
    signature_header: str | None = Header(
        default=None,
        alias="X-Hub-Signature-256",
    ),
) -> WhatsAppWebhookResponse:
    """Authenticate a simplified payload before parsing it."""
    raw_payload = await request.body()

    try:
        authenticate_whatsapp_payload(
            raw_payload=raw_payload,
            signature_header=signature_header,
        )

        decoded_payload = decode_json_payload(
            raw_payload
        )

        try:
            validated_payload = (
                WhatsAppWebhookRequest.model_validate(
                    decoded_payload
                )
            )
        except ValidationError as error:
            raise HTTPException(
                status_code=(
                    status.HTTP_422_UNPROCESSABLE_CONTENT
                ),
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


@app.post(
    "/webhooks/whatsapp/meta",
    response_model=None,
    status_code=status.HTTP_200_OK,
    tags=["WhatsApp"],
)
async def meta_whatsapp_webhook(
    request: Request,
    signature_header: str | None = Header(
        default=None,
        alias="X-Hub-Signature-256",
    ),
) -> JSONResponse:
    """Authenticate and process a complete Meta webhook batch."""
    raw_payload = await request.body()

    try:
        authenticate_whatsapp_payload(
            raw_payload=raw_payload,
            signature_header=signature_header,
        )

        decoded_payload = decode_json_payload(
            raw_payload
        )

        if not isinstance(decoded_payload, dict):
            raise HTTPException(
                status_code=(
                    status.HTTP_422_UNPROCESSABLE_CONTENT
                ),
                detail="Meta webhook payload must be a JSON object.",
            )

        try:
            parsed_batch = parse_meta_whatsapp_batch(
                decoded_payload,
                role="support",
                history_limit=5,
            )
        except MetaWhatsAppNoMessageError:
            response = MetaWhatsAppBatchResponse(
                status="completed",
                received=0,
                processed=0,
                duplicates=0,
                ignored=1,
                unsupported=0,
                failed=0,
                deliveries_sent=0,
                deliveries_failed=0,
                deliveries_skipped=0,
                results=[],
            )

            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content=response.model_dump(mode="json"),
            )

        except MetaWhatsAppPayloadError as error:
            raise HTTPException(
                status_code=(
                    status.HTTP_422_UNPROCESSABLE_CONTENT
                ),
                detail=str(error),
            ) from error

        processed_count = 0
        duplicate_count = 0
        failed_count = 0

        deliveries_sent = 0
        deliveries_failed = 0
        deliveries_skipped = 0

        results: list[
            MetaWhatsAppBatchItemResponse
        ] = []

        for internal_request in parsed_batch.messages:
            try:
                processing_result = process_whatsapp_request(
                    internal_request
                )

                if processing_result.status == "duplicate":
                    duplicate_count += 1
                    deliveries_skipped += 1

                    results.append(
                        build_persisted_delivery_item(
                            processing_result=processing_result,
                            delivery_result=None,
                        )
                    )

                    continue

                processed_count += 1

                delivery_result = persist_and_deliver_reply(
                    inbound_message_id=(
                        processing_result.inbound_message_id
                    ),
                    recipient_phone=(
                        processing_result.sender_phone
                    ),
                    message=processing_result.reply,
                )

                if delivery_result.status == "sent":
                    deliveries_sent += 1
                else:
                    deliveries_failed += 1

                results.append(
                    build_persisted_delivery_item(
                        processing_result=processing_result,
                        delivery_result=delivery_result,
                    )
                )

            except (
                PromptTemplateError,
                ProviderError,
                ValueError,
                OutboundDeliveryStorageError,
            ) as error:
                failed_count += 1
                deliveries_skipped += 1

                results.append(
                    MetaWhatsAppBatchItemResponse(
                        status="failed",
                        inbound_message_id=(
                            internal_request.message_id
                        ),
                        sender_phone=(
                            internal_request.sender_phone
                        ),
                        error=str(error),
                        delivery_status="skipped",
                    )
                )

        response = MetaWhatsAppBatchResponse(
            status="completed",
            received=len(parsed_batch.messages),
            processed=processed_count,
            duplicates=duplicate_count,
            ignored=parsed_batch.ignored_events,
            unsupported=(
                parsed_batch.unsupported_messages
            ),
            failed=failed_count,
            deliveries_sent=deliveries_sent,
            deliveries_failed=deliveries_failed,
            deliveries_skipped=deliveries_skipped,
            results=results,
        )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=response.model_dump(mode="json"),
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


@app.get(
    "/deliveries/retry-pending",
    response_model=RetryPendingDeliveryListResponse,
    status_code=status.HTTP_200_OK,
    tags=["Deliveries"],
)
def get_retry_pending_deliveries(
    limit: int = Query(
        default=DEFAULT_RETRY_LIMIT,
        ge=1,
        le=MAX_RETRY_LIMIT,
    ),
) -> RetryPendingDeliveryListResponse:
    """List outbound deliveries currently waiting for retry."""
    try:
        records = list_retry_pending_deliveries(
            limit=limit
        )

        deliveries = [
            OutboundDeliveryRecordResponse(
                **record
            )
            for record in records
        ]

        return RetryPendingDeliveryListResponse(
            total=len(deliveries),
            limit=limit,
            deliveries=deliveries,
        )

    except (
        ValueError,
        OutboundDeliveryStorageError,
    ) as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error


@app.post(
    "/deliveries/{inbound_message_id}/retry",
    response_model=OutboundRetryItemResponse,
    status_code=status.HTTP_200_OK,
    tags=["Deliveries"],
)
def retry_single_delivery(
    inbound_message_id: str,
) -> OutboundRetryItemResponse:
    """Retry one stored outbound delivery without regenerating AI text."""
    try:
        result = retry_outbound_delivery(
            inbound_message_id=inbound_message_id
        )

        return build_retry_item_response(
            result
        )

    except OutboundDeliveryRetryError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error

    except OutboundDeliveryStorageError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(error),
        ) from error


@app.post(
    "/deliveries/retry-pending",
    response_model=OutboundRetryBatchResponse,
    status_code=status.HTTP_200_OK,
    tags=["Deliveries"],
)
def retry_pending_delivery_batch(
    limit: int = Query(
        default=DEFAULT_RETRY_LIMIT,
        ge=1,
        le=MAX_RETRY_LIMIT,
    ),
) -> OutboundRetryBatchResponse:
    """Retry a limited batch of persisted failed deliveries."""
    try:
        result = retry_pending_deliveries(
            limit=limit
        )

        return OutboundRetryBatchResponse(
            requested=result.requested,
            attempted=result.attempted,
            sent=result.sent,
            failed=result.failed,
            results=[
                build_retry_item_response(item)
                for item in result.results
            ],
        )

    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error

    except OutboundDeliveryStorageError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(error),
        ) from error


@app.get(
    "/conversations",
    response_model=ConversationListResponse,
    status_code=status.HTTP_200_OK,
    tags=["Conversations"],
)
def list_conversations(
    limit: int = Query(
        default=DEFAULT_CONVERSATION_LIMIT,
        ge=1,
        le=MAX_CONVERSATION_LIMIT,
    ),
    offset: int = Query(
        default=0,
        ge=0,
    ),
    search: str | None = Query(
        default=None,
        min_length=1,
        max_length=MAX_CONVERSATION_SEARCH_LENGTH,
        pattern=r".*\S.*",
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
)
def get_conversation(
    session_id: str,
    limit: int = Query(
        default=DEFAULT_MESSAGE_LIMIT,
        ge=1,
        le=MAX_MESSAGE_LIMIT,
    ),
    offset: int = Query(
        default=0,
        ge=0,
    ),
) -> ConversationResponse:
    """Return one paginated page of exchanges for a session."""
    try:
        total = count_messages_by_session(
            session_id
        )

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
)
def delete_conversation(
    session_id: str,
) -> ConversationDeletionResponse:
    """Delete all stored exchanges belonging to a session."""
    try:
        deleted_count = delete_messages_by_session(
            session_id
        )

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