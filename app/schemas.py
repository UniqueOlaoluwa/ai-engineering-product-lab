"""Pydantic models used by the FastAPI application."""

from pydantic import BaseModel, Field


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


class ChatResponse(BaseModel):
    """Define the chatbot response returned by the API."""

    message_id: int
    session_id: str
    role: str
    role_name: str
    reply: str
    provider: str


class HealthResponse(BaseModel):
    """Define the health-check response."""

    status: str
    application: str
    version: str