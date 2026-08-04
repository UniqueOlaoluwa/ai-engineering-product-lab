"""Pydantic models used by the FastAPI application."""

from datetime import datetime

from pydantic import BaseModel, Field


class RootResponse(BaseModel):
    """Define basic API information returned by the root endpoint."""

    application: str
    version: str
    status: str
    documentation: str
    health: str


class ChatRequest(BaseModel):
    """Validate an incoming chatbot request."""

    message: str = Field(
        min_length=1,
        max_length=2000,
        description="The user's message to the assistant.",
        examples=[
            "Help me reduce repetitive customer-support questions."
        ],
    )

    role: str = Field(
        default="support",
        min_length=1,
        max_length=100,
        description="The assistant role requested by the client.",
        examples=["business"],
    )

    session_id: str = Field(
        default="default-session",
        min_length=1,
        max_length=100,
        description="A client-generated conversation session identifier.",
        examples=["demo-session-001"],
    )

    history_limit: int = Field(
        default=5,
        ge=0,
        le=20,
        description=(
            "Maximum number of recent stored exchanges included "
            "as conversation context."
        ),
        examples=[5],
    )


class ChatResponse(BaseModel):
    """Define the chatbot response returned by the API."""

    message_id: int
    session_id: str
    role: str
    role_name: str
    reply: str
    provider: str


class WhatsAppWebhookRequest(BaseModel):
    """Represent a simplified incoming WhatsApp-style message."""

    sender_phone: str = Field(
        min_length=7,
        max_length=20,
        pattern=r"^\+?[0-9]+$",
        description=(
            "Sender phone number using digits and an optional "
            "leading plus sign."
        ),
        examples=["+2348012345678"],
    )

    message: str = Field(
        min_length=1,
        max_length=2000,
        description="Incoming WhatsApp text message.",
        examples=["What time does the clinic open?"],
    )

    message_id: str = Field(
        min_length=1,
        max_length=150,
        description="Provider-generated unique message identifier.",
        examples=["wamid.mock-001"],
    )

    role: str = Field(
        default="support",
        min_length=1,
        max_length=100,
        description="Assistant role used to answer the message.",
        examples=["clinic_admin"],
    )

    history_limit: int = Field(
        default=5,
        ge=0,
        le=20,
        description="Number of recent exchanges used as memory.",
        examples=[5],
    )


class WhatsAppWebhookResponse(BaseModel):
    """Define the response for one WhatsApp-style message."""

    status: str
    inbound_message_id: str
    session_id: str
    sender_phone: str
    reply: str
    provider: str
    stored_message_id: int


class MetaWhatsAppBatchItemResponse(BaseModel):
    """Represent the outcome of processing one Meta message."""

    status: str
    inbound_message_id: str
    sender_phone: str
    session_id: str | None = None
    reply: str | None = None
    provider: str | None = None
    stored_message_id: int | None = None
    error: str | None = None


class MetaWhatsAppBatchResponse(BaseModel):
    """Summarize one complete Meta webhook batch."""

    status: str
    received: int
    processed: int
    duplicates: int
    ignored: int
    unsupported: int
    failed: int
    results: list[MetaWhatsAppBatchItemResponse]


class HealthResponse(BaseModel):
    """Define the health-check response."""

    status: str
    application: str
    version: str


class StoredMessage(BaseModel):
    """Represent one chatbot exchange retrieved from storage."""

    id: int
    role: str
    user_message: str
    assistant_reply: str
    provider: str
    created_at: datetime


class ConversationResponse(BaseModel):
    """Define a paginated stored conversation response."""

    session_id: str
    total: int
    limit: int
    offset: int
    message_count: int
    messages: list[StoredMessage]


class ConversationDeletionResponse(BaseModel):
    """Define the response returned after deleting a conversation."""

    session_id: str
    deleted_count: int
    message: str


class ConversationSummary(BaseModel):
    """Represent one conversation in a paginated listing."""

    session_id: str
    message_count: int
    first_created_at: datetime
    last_created_at: datetime


class ConversationListResponse(BaseModel):
    """Define a paginated list of conversation summaries."""

    total: int
    limit: int
    offset: int
    conversations: list[ConversationSummary]


class ErrorResponse(BaseModel):
    """Define the standard API error response."""

    error: str
    status_code: int
    request_id: str