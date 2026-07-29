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

## Current Architecture

```text
Browser, PowerShell, Website, or External Client
  ↓
FastAPI Endpoint
  ↓
Pydantic Request Validation
  ↓
Role Normalization
  ↓
Prompt Builder
  ↓
JSON Role Configuration
  ↓
Environment Settings
  ↓
Provider Factory
  ↓
Provider Interface
  ↓
Mock Model Provider
  ↓
SQLite Conversation Storage
  ↓
Pydantic Response Model
  ↓
Structured JSON Response
```

The project currently separates:

- FastAPI routes in `app/api.py`
- request and response schemas in `app/schemas.py`
- SQLite storage logic in `app/database.py`
- environment configuration in `.env`
- public configuration examples in `.env.example`
- settings loading in `app/config.py`
- provider creation in `app/providers/factory.py`
- command-line interaction in `app/main.py`
- prompt-building logic in `app/prompt_builder.py`
- custom application errors in `app/exceptions.py`
- JSON loading and validation in `app/templates.py`
- provider interface in `app/providers/base.py`
- mock-provider behaviour in `app/providers/mock.py`
- assistant-role configuration in `data/prompt_templates.json`
- automated tests in `tests/`

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