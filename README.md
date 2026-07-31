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
- uses recent conversation history when generating new responses
- isolates conversation memory by session ID
- limits prompt context to the five most recent exchanges
- prevents formatted prompt context from being duplicated in storage
- allows clients to configure conversation-memory depth
- supports disabling memory for individual chat requests
- validates memory limits between zero and twenty exchanges
- exposes memory constraints through OpenAPI documentation
- deletes stored conversations by session ID
- reports how many messages were removed
- returns a structured 404 when a conversation does not exist
- preserves unrelated sessions during deletion
- lists stored conversation sessions
- returns one summary per conversation
- supports pagination using limit and offset
- orders conversations by recent activity
- uses database indexes for session and date lookups
- searches conversations by session ID
- performs case-insensitive partial matching
- combines search with limit and offset pagination
- returns totals for filtered results
- validates blank and excessive search values
- isolates automated API tests from development data

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

## Conversation-Aware Memory

The `/chat` endpoint can use recent conversation history from the same session.

Example first request:

```json
{
  "message": "What is workflow automation?",
  "role": "business",
  "session_id": "business-demo-001",
  "history_limit": 5
}
```

Example follow-up request:

```json
{
  "message": "Give me an example for a clinic.",
  "role": "business",
  "session_id": "business-demo-001",
  "history_limit": 5
}
```

Before generating the second response, the application retrieves earlier exchanges from `business-demo-001` and formats them as context:

```text
Previous conversation context:
User: What is workflow automation?
Assistant: ...

Current user message:
Give me an example for a clinic.
```

### History-limit rules

The `history_limit` field controls how many recent stored exchanges are included in the prompt.

| Value | Behaviour |
|---|---|
| Omitted | Uses the default limit of `5` |
| `0` | Disables previous context for the current request |
| `1`–`20` | Uses up to that number of recent exchanges |
| Below `0` | Returns a `422` validation error |
| Above `20` | Returns a `422` validation error |

Example with memory disabled:

```json
{
  "message": "Answer without using our earlier discussion.",
  "role": "business",
  "session_id": "business-demo-001",
  "history_limit": 0
}
```

Setting `history_limit` to `0` does not delete conversation history and does not prevent the new exchange from being saved. It only disables previous context for that request.

Conversation history remains isolated by session ID. A request cannot inherit context from another session.

Only the original user message is stored in SQLite. The formatted prompt context is not stored as the new user message.

## Conversation Deletion

A stored conversation can be deleted using:

```text
DELETE /conversations/{session_id}
```

Example:

```text
DELETE /conversations/business-demo-001
```

Successful response:

```json
{
  "session_id": "business-demo-001",
  "deleted_count": 2,
  "message": "Conversation deleted successfully."
}
```

After successful deletion, retrieving the same session returns:

```text
404 Not Found
```

Unknown sessions also return a structured error:

```json
{
  "error": "Conversation session not found.",
  "status_code": 404,
  "request_id": "client-request-123"
}
```

Deletion affects only messages matching the supplied session ID. Other conversations remain unchanged.

The database layer uses a parameterized query:

```sql
DELETE FROM messages
WHERE session_id = ?
```

This avoids unsafe SQL string construction.

## Conversation Listing

Stored conversation sessions can be listed using:

```text
GET /conversations
```

The endpoint accepts two query parameters:

| Parameter | Default | Allowed values | Purpose |
|---|---:|---:|---|
| `limit` | `20` | `1–100` | Maximum number of conversations returned |
| `offset` | `0` | `0` or greater | Number of conversation summaries skipped |

Example:

```text
GET /conversations?limit=20&offset=0
```

Example response:

```json
{
  "total": 3,
  "limit": 20,
  "offset": 0,
  "conversations": [
    {
      "session_id": "clinic-demo-001",
      "message_count": 4,
      "first_created_at": "2026-07-30T12:00:00",
      "last_created_at": "2026-07-30T12:15:00"
    }
  ]
}
```

Each summary contains:

- session ID
- number of stored exchanges
- first activity time
- latest activity time

Conversation summaries are ordered by most recent activity.

Invalid pagination values return structured `422` validation errors.

Examples:

```text
limit=0
limit=101
offset=-1
```

The database uses indexes on `session_id` and `created_at` to improve lookup performance as stored data grows.

## Conversation Search

The conversation-listing endpoint supports optional session-ID search:

```text
GET /conversations?search=clinic
```

Search is:

- case-insensitive
- based on partial session-ID matches
- compatible with pagination
- limited to one hundred characters

Example:

```text
GET /conversations?search=clinic&limit=20&offset=0
```

A search for `clinic` may match:

```text
clinic-demo-001
CLINIC-support-session
customer-clinic-assistant
```

The `total` field represents every matching session, not only the records returned on the current page.

Search and pagination can be combined:

```text
GET /conversations?search=clinic&limit=1&offset=0
GET /conversations?search=clinic&limit=1&offset=1
```

Invalid searches return structured `422` validation errors.

Examples:

```text
search containing only spaces
search longer than 100 characters
```

The database query remains parameterized:

```sql
WHERE LOWER(session_id) LIKE LOWER(?)
```

Automated API tests use separate project-local SQLite databases inside `.test_storage`. This prevents test runs from filling the development database.

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
Client sends message, role, session ID, and optional history limit
  ↓
Request middleware validates or generates a request ID
  ↓
Pydantic validates the request body
  ↓
history_limit is checked against the allowed range of 0–20
  ↓
Environment settings are loaded
  ↓
Provider factory selects the configured provider
  ↓
Assistant role is normalized
  ↓
SQLite retrieves stored messages for the session
  ↓
Conversation-context layer selects the requested number of recent exchanges
  ↓
If history_limit is 0, only the current message is used
  ↓
Previous exchanges and the current message are formatted together
  ↓
Prompt builder creates a role-specific prompt
  ↓
Provider generates a response
  ↓
Original user message and assistant response are saved in SQLite
  ↓
Pydantic validates the response
  ↓
FastAPI returns JSON with an X-Request-ID header
```
### Request flow for conversation listing

```text
Client sends GET /conversations with limit and offset
  ↓
Request middleware validates or generates a request ID
  ↓
FastAPI validates pagination query parameters
  ↓
Database counts distinct conversation sessions
  ↓
Database groups messages by session ID
  ↓
COUNT calculates the number of exchanges
  ↓
MIN finds the first activity time
  ↓
MAX finds the latest activity time
  ↓
Results are ordered by recent activity
  ↓
Limit and offset are applied
  ↓
Pydantic validates conversation summaries
  ↓
FastAPI returns paginated JSON with X-Request-ID
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

### Request flow for conversation deletion

```text
Client sends DELETE /conversations/{session_id}
  ↓
Request middleware validates or generates a request ID
  ↓
FastAPI captures the session ID path parameter
  ↓
Database layer runs a parameterized DELETE query
  ↓
Deleted row count is returned
  ↓
If deleted count is zero, API returns structured 404
  ↓
If messages were deleted, API returns session ID and deleted count
  ↓
Response includes X-Request-ID
```
### Request flow for conversation search

```text
Client sends GET /conversations with optional search
  ↓
FastAPI validates limit, offset, and search constraints
  ↓
Search value is trimmed and normalized
  ↓
Database uses a parameterized partial-match condition
  ↓
Count query calculates matching session total
  ↓
Listing query groups matching messages by session ID
  ↓
Conversation summaries are ordered by recent activity
  ↓
Limit and offset are applied
  ↓
FastAPI returns filtered pagination metadata and summaries
```

### Automated test isolation

```text
Pytest starts one API test
  ↓
An isolated SQLite database is created inside .test_storage
  ↓
The test writes only to that temporary database
  ↓
The development database remains unchanged
  ↓
The next API test receives a different isolated database
```

### Main application files

- `app/api.py` — FastAPI application, routes, HTTP errors, and middleware registration
- `app/schemas.py` — request and response validation models
- `app/middleware.py` — request IDs, tracing, and request-completion logging
- `app/logging_config.py` — centralized application logger configuration
- `app/database.py` — SQLite storage, indexes, retrieval, deletion, pagination, session counting, and conversation search
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
```markdown
- `app/conversation_context.py` — recent-message selection and multi-turn prompt context
- `tests/test_conversation_context.py` — conversation-context unit tests
- `tests/test_conversation_listing.py` — database tests for grouped conversation summaries and pagination
- `tests/conftest.py` — shared pytest configuration for isolated, project-local API test databases

### Current API endpoints

| Method | Endpoint | Group | Purpose |
|---|---|---|---|
| `GET` | `/` | System | Returns API information and useful paths |
| `GET` | `/health` | System | Reports whether the API is running |
| `POST` | `/chat` | Chat | Generates and saves a role-specific response |
| `GET` | `/conversations` | Conversations | Lists, searches and paginates conversation summaries |
| `GET` | `/conversations/{session_id}` | Conversations | Retrieves saved conversation history |
| `DELETE` | `/conversations/{session_id}` | Conversations | Deletes all messages in a conversation |

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