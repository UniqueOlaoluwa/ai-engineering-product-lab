"""FastAPI application for the AI Engineering Product Lab."""

from fastapi import FastAPI

API_VERSION = "0.2.0"

app = FastAPI(
    title="AI Engineering Product Lab API",
    description=(
        "A learning API for building practical AI assistants, "
        "business automation systems, and WhatsApp-style applications."
    ),
    version=API_VERSION,
)


@app.get("/health")
def health_check() -> dict[str, str]:
    """Return the current application health status."""
    return {
        "status": "ok",
        "application": "AI Engineering Product Lab",
        "version": API_VERSION,
    }