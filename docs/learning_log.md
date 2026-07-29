# AI Engineering Learning Log

## Day 1 — Project Setup and First Application

### What I built

- Created a separate AI Engineering project in VS Code
- Created and activated a Python virtual environment
- Organized the project into app, data, docs, and tests folders
- Protected secrets and generated files with .gitignore
- Built a command-line mock AI assistant
- Initialized Git and pushed the project to GitHub

### Concepts practised

- Project isolation
- Python virtual environments
- Python functions
- User input
- Loops and conditionals
- Git commits
- GitHub repositories
- Secret protection

---

## Day 2 — Role-Based Prompt Builder

### What I built

- Added business, customer-support, and clinic-admin roles
- Separated prompt-building logic from the command-line interface
- Added role normalization and safe fallback behaviour
- Added input validation and exception handling

### Concepts practised

- Python dictionaries
- Functions with parameters and return values
- Imports between Python modules
- Type hints
- Exceptions
- Modular application structure
- Selective Git staging

---

## Day 3 — JSON Prompt Configuration

### What I built

- Moved assistant roles from Python into a JSON configuration file
- Created a reusable JSON template loader
- Added validation for missing or invalid configuration
- Loaded role names and instructions dynamically
- Added an AI Builders Network learning-assistant role without changing the main application logic

### Concepts practised

- JSON objects
- Nested dictionaries
- Reading files with Python
- pathlib file paths
- JSON parsing
- Configuration validation
- Runtime errors
- Configuration-driven development

### Key lesson

Application logic and client-specific configuration should not always be mixed together.

The Python code controls how the assistant works, while the JSON file controls which assistant roles and instructions are available.

---

## Day 4 — Custom Errors and Safe Startup

### What I built

- Created custom exceptions for prompt-template failures
- Added detailed validation for JSON configuration structure
- Added lazy configuration loading
- Cached the loaded configuration in memory
- Separated application startup from the interactive assistant
- Added user-friendly handling for configuration failures
- Tested missing files, invalid structures, and controlled startup errors

### Concepts practised

- Custom Python exceptions
- Exception inheritance
- Defensive configuration validation
- Lazy loading
- Function caching
- Safe application startup
- Controlled failure testing
- User-friendly error messages

### Key lesson

A reliable application should not fail with an unclear technical traceback when a predictable configuration problem occurs.

The application should identify the type of failure, explain what went wrong, and tell the developer what to check.

---

## Day 5 — Replaceable Model Providers

### What I built

- Created a provider package
- Added an abstract base class for AI model providers
- Created a mock provider for local development
- Added simulated timeout and request failures
- Connected the provider to the command-line assistant
- Kept provider failures from closing the application

### Concepts practised

- Python classes
- Constructors
- Instance variables
- Inheritance
- Abstract base classes
- Dependency injection
- Provider interfaces
- Controlled service-failure testing

### Key lesson

The application should depend on a stable provider interface rather than one specific AI company.

The assistant can call `provider.generate(prompt)` while the provider decides how the response is produced.

---

## Day 6 — Environment Configuration and Provider Factory

### What I built

- Installed python-dotenv
- Created a private local .env configuration file
- Added structured application settings with a dataclass
- Added environment-variable normalization
- Created a provider factory
- Selected the model provider through configuration
- Added safe handling for unsupported provider settings
- Confirmed that the private .env file is ignored by Git

### Concepts practised

- Environment variables
- Secret separation
- .env files
- Python dataclasses
- Optional configuration values
- Dependency management
- Provider factories
- Configuration-based application behaviour

### Key lesson

Application settings and secrets should not be hard-coded inside source files.

The application can read configuration from its environment and create the correct provider without changing the main interaction logic.

---

## Day 6 — Environment Configuration and Provider Factory

### What I built

- Installed python-dotenv
- Created a private local .env configuration file
- Added structured application settings with a dataclass
- Added environment-variable normalization
- Created a provider factory
- Selected the model provider through configuration
- Added safe handling for unsupported provider settings
- Confirmed that the private .env file is ignored by Git
- Debugged a temporary terminal environment-variable override

### Concepts practised

- Environment variables
- Secret separation
- .env files
- Python dataclasses
- Optional configuration values
- Dependency management
- Provider factories
- Configuration precedence
- Configuration-based application behaviour

### Key lesson

Application settings and secrets should not be hard-coded inside source files.

Existing terminal environment variables can override values loaded from a .env file, so temporary test variables must be removed after testing.

---

## Day 7 — Automated Testing and Week 1 Release

### What I built

- Installed pytest
- Added automated tests for role normalization
- Tested prompt generation and clinic safety instructions
- Tested empty-message validation
- Tested normal mock-provider responses
- Tested provider timeout and request failures
- Tested environment configuration helpers
- Confirmed the complete command-line application still works

### Concepts practised

- Automated testing
- pytest
- Test discovery
- Arrange, Act, Assert
- Assertions
- Testing exceptions
- Test fixtures
- Environment-variable testing with monkeypatch
- Regression prevention

### Key lesson

Manual testing confirms that a user flow works today.

Automated tests preserve expected behaviour and warn me when a future change breaks something that previously worked.

---

## Day 8 — First FastAPI Backend

### What I built

- Installed FastAPI and its development server
- Created a FastAPI application
- Added a GET /health endpoint
- Returned structured JSON from Python
- Started a local development server
- Tested the API from a browser
- Used FastAPI interactive documentation
- Called the API from PowerShell
- Added an automated API test with TestClient

### Concepts practised

- APIs
- HTTP requests
- HTTP GET methods
- Endpoints
- Local web servers
- Ports
- JSON responses
- HTTP status codes
- FastAPI route decorators
- Interactive API documentation
- Automated endpoint testing

### Key lesson

An API gives other systems a structured way to communicate with my application.

The command-line interface is useful for local interaction, while the FastAPI backend can later receive requests from WhatsApp, websites, mobile applications, and business systems.

---

## Day 9 — Chatbot API Endpoint

### What I built

- Created Pydantic request and response models
- Added a POST /chat endpoint
- Accepted structured JSON requests
- Added role selection and safe fallback behaviour
- Connected the API to the prompt builder
- Connected the API to the configured model provider
- Returned structured JSON responses
- Added request validation for empty, missing, and invalid message values
- Added HTTP error handling for provider and configuration failures
- Expanded automated API tests

### Concepts practised

- HTTP POST requests
- JSON request bodies
- Pydantic models
- Request validation
- Response models
- HTTP status codes
- FastAPI error handling
- Structured API responses
- API integration testing

### Key lesson

An API endpoint should define and validate both the data it accepts and the data it returns.

FastAPI and Pydantic can reject malformed requests before they reach the main application logic.

---

## Day 10 — SQLite Conversation Storage

### What I built

- Added a local SQLite conversation database
- Created a messages table
- Saved chatbot exchanges after successful API requests
- Added session IDs to group related conversations
- Returned database message IDs in API responses
- Added retrieval of saved messages by session
- Added database tests with isolated test storage
- Fixed Windows file-lock problems by explicitly closing SQLite connections
- Confirmed the full test suite passes

### Concepts practised

- SQLite
- Relational tables
- Rows and columns
- SQL CREATE TABLE
- SQL INSERT
- SQL SELECT
- Parameterized SQL
- Persistent application state
- Session identifiers
- Database connection management
- Test isolation
- Windows file locking

### Key lesson

A database makes application state persistent after the server stops.

SQLite connections must be closed explicitly on Windows before test database files can be deleted safely.

---

## Day 11 — Conversation History Endpoint

### What I built

- Added a conversation-history response model
- Added a stored-message response model
- Added `GET /conversations/{session_id}`
- Retrieved saved exchanges by session ID
- Returned a 404 response for unknown sessions
- Added API integration tests for conversation retrieval
- Confirmed nested response validation with Pydantic

### Concepts practised

- FastAPI path parameters
- Nested Pydantic models
- Lists of structured records
- HTTP 404 responses
- Database retrieval through an API
- API integration testing
- Separation between route logic and SQL logic

### Key lesson

The database layer returns raw application data, while the API layer decides how that data should be presented over HTTP.

An empty database result can therefore become a `404 Not Found` response at the API boundary.

---

## Day 12 — Request IDs and Structured Logging

### What I built

- Added centralized application logging
- Added HTTP request-logging middleware
- Generated a unique UUID for requests without an identifier
- Preserved valid request IDs supplied by clients
- Returned request IDs through the `X-Request-ID` response header
- Logged request method, path, status code, and duration
- Added request IDs to failed-request logs
- Validated client request IDs before writing them to logs
- Replaced unsafe or overly long request IDs with generated UUIDs
- Added middleware and request-ID tests

### Concepts practised

- FastAPI middleware
- Request and response lifecycle
- UUID generation
- HTTP headers
- Structured logging
- Request tracing
- Duration measurement
- Regular expressions
- Input validation
- Log-injection prevention
- Middleware integration testing

### Key lesson

Logs become much easier to investigate when every request has a traceable identifier.

Even values used only for logging should be treated as untrusted input and validated before use.