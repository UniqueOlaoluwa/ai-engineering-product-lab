# AI Engineering Product Lab

A project-based AI Engineering learning repository created by Orobiyi Olaoluwa Ayomide.

## Purpose

This repository documents my transition from practical AI product thinking and AI-assisted development into stronger AI Engineering.

The goal is to build real AI applications that can become:

- AI WebCo client demonstrations
- SME customer-support assistants
- WhatsApp AI assistants
- clinic AI receptionist systems
- document Q&A tools
- AI Builders Network teaching projects

## Current Project

### Project 1: Configurable AI Prompt Assistant

The current command-line application:

- accepts user messages
- loads assistant roles from JSON configuration
- supports business, customer-support, clinic-admin, and AI-learning roles
- validates empty input
- uses safe fallback behaviour for unknown roles
- separates application logic from prompt configuration
- runs with a mock model provider and requires no paid AI API
- validates the structure of its JSON configuration
- uses custom exceptions for configuration failures
- loads and caches configuration safely
- displays useful startup messages instead of crashing on known configuration errors
- uses a replaceable AI model provider interface
- includes a mock provider for development without API costs
- handles provider timeouts and request failures without closing the application
- loads application settings from environment variables
- keeps private configuration in a Git-ignored .env file
- selects the model provider through a provider factory
- handles unsupported provider configuration safely
- loads application settings from environment variables
- keeps private configuration in a Git-ignored `.env` file
- selects the model provider through a provider factory
- handles unsupported provider configuration safely
- includes automated tests for prompts, configuration, and provider behaviour
- verifies expected failures such as empty input, provider timeouts, and invalid requests
- includes a FastAPI backend
- exposes a health-check endpoint
- returns structured JSON responses
- provides interactive API documentation
- includes automated endpoint testing
- exposes a POST /chat endpoint
- accepts validated JSON requests
- returns structured chatbot responses
- supports configurable assistant roles through the API
- rejects malformed or incomplete requests automatically
- stores successful chatbot exchanges in SQLite
- groups conversations using session identifiers
- returns database message IDs in chat responses
- keeps local database files out of Git
- includes isolated database tests
- retrieves saved conversation history by session ID
- returns 404 responses for unknown conversation sessions
- validates nested conversation responses with Pydantic
- assigns a traceable request ID to every HTTP request
- returns request IDs through the `X-Request-ID` response header
- records structured request-completion logs
- validates client-supplied request IDs before logging
- returns consistent structured API error responses
- includes request IDs in error bodies and headers
- handles both HTTP errors and request-validation failures centrally
- provides a root endpoint with API information
- groups Swagger endpoints into System, Chat, and Conversations
- exposes versioned API metadata
- documents endpoint purposes through OpenAPI summaries

## API Discovery

The root endpoint provides basic information about the running API:

```text
GET /
```

Example response:

```json
{
  "application": "AI Engineering Product Lab",
  "version": "0.6.0",
  "status": "running",
  "documentation": "/docs",
  "health": "/health"
}
```

Interactive API documentation is available at:

```text
http://127.0.0.1:8000/docs
```

The endpoints are grouped into:

- `System` — root and health endpoints
- `Chat` — role-based response generation and storage
- `Conversations` — saved conversation-history retrieval

## Current Architecture

```text
Client
  │
  │  HTTP request
  │  Optional X-Request-ID header
  ▼
Request-ID and Logging Middleware
  │
  ├── validates a client-provided request ID
  ├── generates a UUID when an ID is missing or unsafe
  ├── records request method, path, status, and duration
  └── adds X-Request-ID to the response
  │
  ▼
FastAPI Route Layer
  │
  ├── GET /health
  ├── POST /chat
  └── GET /conversations/{session_id}
  │
  ▼
  Centralized Error Handlers
  ├── HTTP exceptions
  ├── request-validation errors
  └── structured errors with request IDs
  │
  ▼
Pydantic Validation Layer
  │
  ├── validates incoming chat requests
  ├── applies default role and session values
  ├── validates structured API responses
  └── validates nested conversation-history records
  │
  ▼
Application Logic
  │
  ├── loads environment settings
  ├── normalizes assistant roles
  ├── loads role configuration
  ├── builds role-specific prompts
  └── converts application errors into HTTP responses
  │
  ▼
Provider Factory
  │
  └── selects the configured language-model provider
  │
  ▼
Provider Interface
  │
  └── defines a consistent generate() contract
  │
  ▼
Mock LLM Provider
  │
  └── generates local test responses without a paid API
  │
  ▼
SQLite Data Layer
  │
  ├── creates the messages table
  ├── saves successful chatbot exchanges
  ├── assigns database message IDs
  └── retrieves conversation history by session ID
  │
  ▼
Structured API Response
  │
  ├── validated JSON response body
  └── X-Request-ID response header
  │
  ▼
Client
```

### Request flow for `POST /chat`

```text
Client sends message, role, and session ID
  ↓
Middleware assigns and logs a request ID
  ↓
Pydantic validates the request body
  ↓
Environment settings are loaded
  ↓
Provider factory selects the configured provider
  ↓
Role is normalized
  ↓
Role configuration is loaded from JSON
  ↓
Prompt builder creates a role-specific prompt
  ↓
Provider generates a response
  ↓
Conversation is saved in SQLite
  ↓
Pydantic validates the response
  ↓
FastAPI returns JSON with X-Request-ID
```

### Request flow for conversation retrieval

```text
Client requests GET /conversations/{session_id}
  ↓
Middleware assigns and logs a request ID
  ↓
FastAPI captures the session ID path parameter
  ↓
Database layer retrieves matching messages
  ↓
API returns 404 when the session does not exist
  ↓
Stored messages are converted into Pydantic models
  ↓
FastAPI returns structured conversation history
```

### Main application files

- `app/api.py` — FastAPI application, routes, HTTP errors, and middleware registration
- `app/schemas.py` — request and response validation models
- `app/middleware.py` — request IDs, tracing, and request-completion logging
- `app/logging_config.py` — centralized application logger configuration
- `app/database.py` — SQLite connection, table creation, saving, and retrieval
- `app/config.py` — environment-variable and application-settings loading
- `app/prompt_builder.py` — role normalization and prompt construction
- `app/templates.py` — JSON role-template loading and validation
- `app/exceptions.py` — custom application and provider exceptions
- `app/providers/base.py` — abstract provider interface
- `app/providers/mock.py` — free local mock provider
- `app/providers/factory.py` — provider selection and creation
- `app/main.py` — command-line application entry point
- `data/prompt_templates.json` — configurable assistant roles and instructions
- `tests/test_api.py` — API route and integration tests
- `tests/test_database.py` — SQLite persistence tests
- `tests/test_middleware.py` — request tracing and middleware-security tests
- `tests/test_config.py` — environment-configuration tests
- `tests/test_prompt_builder.py` — prompt and role-behaviour tests
- `tests/test_mock_provider.py` — provider-behaviour tests

### Current API endpoints

| Method | Endpoint | Group | Purpose |
|---|---|---|---|
| `GET` | `/` | System | Returns API information and useful paths |
| `GET` | `/health` | System | Reports whether the API is running |
| `POST` | `/chat` | Chat | Generates and saves a role-specific response |
| `GET` | `/conversations/{session_id}` | Conversations | Retrieves saved conversation history |

### Current storage

The project uses a local SQLite database:

```text
storage/conversations.db
```

The database currently stores:

- message ID
- session ID
- assistant role
- user message
- assistant response
- provider name
- creation time

Local databases and temporary test databases are excluded from Git.

### Current provider configuration

The project currently uses:

```text
LLM_PROVIDER=mock
```

The mock provider allows the complete application flow to be developed and tested without API costs.

The provider interface and factory allow a real provider to be added later without rewriting the API, prompt builder, database layer, or tests.

## Run Locally

Create and activate a Python virtual environment.

On Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Run the application:

```powershell
python -m app.main
```

## Current Folder Structure

```text
ai-engineering-product-lab/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── prompt_builder.py
│   └── templates.py
├── data/
│   └── prompt_templates.json
├── docs/
│   └── learning_log.md
├── tests/
├── .env.example
├── .gitignore
├── README.md
└── requirements.txt
```

## Run Tests

Run the complete automated test suite:

```powershell
python -m pytest
```

Run the tests with individual test names displayed:

```powershell
python -m pytest -v
```

The tests currently cover:

- environment configuration
- role normalization and fallback behaviour
- prompt generation
- clinic safety instructions
- empty-input validation
- mock-provider responses
- provider timeout and request failures

## Run the API

Start the local FastAPI development server:

```powershell
fastapi dev app\api.py
```

Open the health endpoint:

```text
http://127.0.0.1:8000/health
```

Open the interactive API documentation:

```text
http://127.0.0.1:8000/docs
```

The current health response is:

```json
{
  "status": "ok",
  "application": "AI Engineering Product Lab",
  "version": "0.2.0"
}
```
## Chat API

Send a chatbot request to:

```text
POST http://127.0.0.1:8000/chat
```

Example request:

```json
{
  "message": "Help me reduce repetitive customer questions.",
  "role": "business"
}
```

Example response structure:

```json
{
  "role": "business",
  "role_name": "Business Assistant",
  "reply": "[Mock provider response] ...",
  "provider": "MockLLMProvider"
}
```

The supported roles are loaded from:

```text
data/prompt_templates.json
```

When no role is supplied, the API uses the configured default role.

Malformed requests are rejected with validation responses before the main chatbot logic runs.

## Conversation Storage

Successful chatbot requests are stored in a local SQLite database:

```text
storage/conversations.db
```

Each saved exchange contains:

- message ID
- session ID
- assistant role
- user message
- assistant response
- provider name
- creation time

The database is excluded from Git and must not contain real patient or confidential client information during development.

Example chat request:

```json
{
  "message": "How can I reduce repeated delivery questions?",
  "role": "business",
  "session_id": "demo-session-001"
}
```

The API returns the saved record identifier:

```json
{
  "message_id": 1,
  "session_id": "demo-session-001",
  "role": "business",
  "role_name": "Business Assistant",
  "reply": "[Mock provider response] ...",
  "provider": "MockLLMProvider"
}
```
## Conversation History Endpoint

Stored conversations can be retrieved using:

```text
GET /conversations/{session_id}
```

Example:

```text
GET /conversations/demo-session-001
```

Successful response:

```json
{
  "session_id": "demo-session-001",
  "message_count": 1,
  "messages": [
    {
      "id": 1,
      "role": "business",
      "user_message": "How can I improve customer support?",
      "assistant_reply": "[Mock provider response] ...",
      "provider": "MockLLMProvider",
      "created_at": "2026-07-29T12:00:00"
    }
  ]
}
```

Unknown sessions return:

```json
{
  "detail": "Conversation session not found."
}
```

with HTTP status:

```text
404 Not Found
```
## Request Tracing

Every HTTP request receives a request identifier.

When the client does not provide one, the application generates a UUID:

```text
X-Request-ID: b349fb6a-48cc-4e4a-88c9-9fc2fa07bccc
```

Clients may provide their own safe identifier:

```text
X-Request-ID: client-request-123
```

Accepted client identifiers may contain:

- letters
- numbers
- hyphens
- underscores
- periods

They must contain no more than 64 characters. Unsafe values are replaced with generated UUIDs.

The same identifier appears in request logs:

```text
request_completed request_id=client-request-123 method=GET path=/health status_code=200 duration_ms=3.42
```

This allows one API request to be traced across client responses and server logs.

## Error Responses

The API returns a consistent error structure for controlled HTTP errors.

Example:

```json
{
  "error": "Conversation session not found.",
  "status_code": 404,
  "request_id": "client-request-123"
}
```

Request-validation errors also use the standard structure:

```json
{
  "error": "Request validation failed.",
  "status_code": 422,
  "request_id": "client-request-123",
  "details": [
    {
      "type": "string_too_short",
      "loc": ["body", "message"],
      "msg": "String should have at least 1 character"
    }
  ]
}
```

The same request ID is returned in the response header:

```text
X-Request-ID: client-request-123
```

This allows clients to report one identifier that can be matched with server logs.

## Current Release

Current application version:

```text
0.6.0
```

This release includes:

- role-based prompt construction
- configurable JSON assistant roles
- provider abstraction and mock provider
- FastAPI endpoints
- request and response validation
- SQLite conversation persistence
- conversation-history retrieval
- request IDs and structured logging
- centralized HTTP and validation-error responses
- interactive OpenAPI documentation
- automated application, API, database, provider, prompt, and middleware tests

## Product Roadmap

1. AI Prompt Assistant
2. Simple AI Chatbot API
3. Business FAQ Bot
4. Document Q&A and RAG Bot
5. WhatsApp-Style AI Assistant
6. Clinic AI Receptionist Demo
7. Maternal-Care WhatsApp Assistant
8. SME Customer-Support Automation Bot
9. Deployed Portfolio Project
10. Client-Ready AI WebCo Demo Package

## Current Assistant Roles

The available assistant roles are stored in:

```text
data/prompt_templates.json
```

Current roles:

- Business Assistant
- Customer Support Assistant
- Clinic Administrative Assistant
- AI Builders Network Learning Assistant

New assistant roles can be added through JSON configuration without rewriting the main application logic.

## Safety

This repository must use synthetic demonstration data during development.

Do not commit:

- API keys
- passwords
- `.env` files
- patient information
- confidential client information
- private access tokens
- database credentials

The clinic-administration role must not diagnose, prescribe, interpret laboratory results, or make clinical decisions.

## Learning Documentation

Development progress and concepts practised are recorded in:

```text
docs/learning_log.md
```

## Author

Orobiyi Olaoluwa Ayomide  
Founder, AI WebCo and AI Builders Network