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

---

## Day 13 — Consistent API Error Responses

### What I built

- Added a standard API error-response model
- Added centralized HTTP exception handling
- Added centralized request-validation error handling
- Included request IDs in error response bodies and headers
- Logged controlled HTTP and validation errors
- Preserved safe client-supplied request IDs
- Replaced unsafe request IDs before returning error responses
- Added tests for 404 and 422 error responses

### Concepts practised

- FastAPI exception handlers
- HTTPException handling
- RequestValidationError handling
- Standard API error contracts
- Request-ID correlation
- Structured warning logs
- HTTP 404 and 422 responses
- Integration testing for errors

### Key lesson

A production API should return predictable error responses.

Using the same structure for controlled errors and validation failures makes client integration and debugging easier.

---

## Day 14 — API Metadata and Release Hardening

### What I built

- Added a root API-information endpoint
- Added a structured root-response model
- Updated the application version to `0.6.0`
- Added API title, summary, description, contact, and licence metadata
- Grouped endpoints in Swagger using tags
- Added clearer endpoint summaries
- Added automated tests for the root endpoint
- Verified that request tracing applies to the root endpoint
- Prepared the project for a tagged release

### Concepts practised

- Semantic versioning
- API metadata
- OpenAPI documentation
- Swagger endpoint grouping
- Root discovery endpoints
- Response-model validation
- Release preparation
- Regression testing

### Key lesson

A working API should also be easy for other developers to discover and understand.

Clear metadata, endpoint grouping, versioning, documentation, and automated tests make a backend easier to maintain and present professionally.

---

## Day 15 — Conversation-Aware Chat Memory

### What I built

- Added conversation-context utilities
- Retrieved previous exchanges before generating a new response
- Included recent conversation history in the next prompt
- Limited prompt context to the five most recent exchanges
- Kept conversation memory isolated by session ID
- Stored only the original user message instead of duplicated prompt context
- Added unit tests for context selection and formatting
- Added API integration tests for multi-turn memory
- Added unique session IDs to improve test reliability
- Updated the application version to `0.7.0`

### Concepts practised

- Multi-turn conversation memory
- Session-based context isolation
- Retrieval-augmented prompt construction
- Context-window limits
- Prompt formatting
- Database-backed memory
- Unit testing
- Integration testing
- Test isolation with UUIDs

### Key lesson

Saving conversations is not the same as using conversation memory.

A conversation-aware assistant must retrieve relevant previous exchanges, format them safely, and include them in the next prompt without mixing sessions or storing duplicated context.

---

## Day 16 — Configurable Conversation Memory

### What I built

- Added a `history_limit` field to chat requests
- Set a default history limit of five exchanges
- Allowed memory to be disabled for individual requests
- Limited the maximum history value to twenty exchanges
- Added API validation for negative and excessive limits
- Exposed the memory limits through OpenAPI documentation
- Added tests for default, minimum, maximum, and invalid values
- Confirmed that disabling prompt memory does not disable message storage
- Updated the application version to `0.8.0`

### Concepts practised

- Per-request AI behaviour controls
- Pydantic numeric constraints
- Minimum and maximum validation
- Boundary-value testing
- OpenAPI schema generation
- Prompt memory versus persistent storage
- Configurable context windows
- API integration testing

### Key lesson

Conversation memory and conversation storage are different features.

A request can disable the use of previous messages while still saving the new exchange for future retrieval.

---

## Day 17 — Conversation Deletion and Data Lifecycle

### What I built

- Added database support for deleting all messages in a session
- Added `DELETE /conversations/{session_id}`
- Returned the number of deleted messages
- Returned a structured `404` response for unknown sessions
- Confirmed that deleting one session does not affect another
- Added database and API tests for deletion
- Verified that deleted conversations can no longer be retrieved
- Updated the application version to `0.9.0`

### Concepts practised

- SQL DELETE statements
- Data lifecycle management
- RESTful deletion endpoints
- Session isolation
- Deletion-count reporting
- Structured 404 errors
- Database testing
- API integration testing

### Key lesson

Applications that store user data should also provide a controlled way to remove it.

Deleting one conversation must remove only that session’s records and must not affect unrelated sessions.

---

## Day 18 — Conversation Listing and Pagination

### What I built

- Added database indexes for session IDs and creation times
- Added distinct conversation-session counting
- Added grouped conversation summaries
- Added pagination using `limit` and `offset`
- Added `GET /conversations`
- Ordered conversation summaries by recent activity
- Added validation for pagination boundaries
- Added database and API tests for listing behaviour
- Updated the application version to `0.10.0`

### Concepts practised

- SQL grouping
- SQL aggregate functions
- `COUNT`, `MIN`, and `MAX`
- Database indexes
- Pagination
- Query parameters
- Boundary validation
- Conversation summaries
- API integration testing

### Key lesson

A conversation dashboard should retrieve summaries instead of loading every message from every session.

Pagination and database indexes help keep listing operations controlled as stored data grows.

---

## Day 19 — Conversation Search and Filtering

### What I built

- Added optional conversation search
- Added case-insensitive session-ID matching
- Added partial-text matching
- Combined conversation search with pagination
- Added filtered conversation counting
- Added search normalization and validation
- Rejected blank searches
- Limited search values to one hundred characters
- Added database and API integration tests
- Isolated API tests from the development database
- Updated the application version to `0.11.0`

### Concepts practised

- Optional API filters
- SQL `LIKE`
- Case-insensitive matching
- Partial-string searching
- Parameterized SQL
- Input normalization
- Search pagination
- Filtered result counts
- OpenAPI query validation
- SQLite test isolation
- Resource-aware testing

### Key lesson

Filtered pagination requires the count query and listing query to use the same search conditions.

Automated API tests should also use isolated databases so repeated tests do not pollute development data or place unnecessary load on the computer.

---

## Day 20 — Message Pagination Within Conversations

### What I built

- Added pagination for messages inside a conversation
- Added default and maximum message-page limits
- Added total message counting per session
- Added paginated message retrieval using limit and offset
- Updated `GET /conversations/{session_id}`
- Added pagination metadata to conversation responses
- Preserved structured 404 behaviour for missing sessions
- Added focused database and API tests
- Updated the application version to `0.12.0`

### Concepts practised

- Nested-resource pagination
- SQL `LIMIT` and `OFFSET`
- Message counting
- Response metadata
- Session isolation
- Query-parameter validation
- Modular database architecture
- OpenAPI pagination constraints
- Resource-aware testing

### Key lesson

A conversation may contain many stored exchanges.

Returning only the requested page reduces response size, database work, and memory usage while still reporting the total number of stored messages.

---

## Day 21 — Reusable Chat Service and Mock WhatsApp Webhook

### What I built

- Moved chatbot processing into a reusable service layer
- Added `app/chat_service.py`
- Refactored `/chat` to use the chat service
- Added a mock WhatsApp webhook endpoint
- Added WhatsApp-style payload validation
- Added phone-number normalization
- Created stable WhatsApp session IDs from phone numbers
- Added webhook-event storage
- Added duplicate-message protection
- Returned stored responses for duplicate webhook deliveries
- Prevented duplicate messages from calling the AI service twice
- Added a lightweight SQLite migration for webhook metadata
- Added focused service, webhook, and idempotency tests
- Updated the application version to `0.14.0`

### Concepts practised

- Service-layer architecture
- Transport-independent business logic
- Webhook processing
- Idempotency
- Duplicate-event detection
- SQLite unique constraints
- Lightweight database migration
- Stable session mapping
- Dependency mocking
- Structured error translation
- Resource-aware testing

### Key lesson

Webhook providers may deliver the same event more than once.

A production-ready webhook must use the provider message ID to detect duplicates and return the original result without processing or saving the message again.

---

## Day 22 — WhatsApp Webhook Verification and Signature Security

### What I built

- Added WhatsApp webhook callback verification
- Added `GET /webhooks/whatsapp`
- Added support for Meta-style query parameters
- Added private webhook verification-token configuration
- Added constant-time token comparison
- Added HMAC-SHA256 request-signature generation
- Added incoming webhook-signature verification
- Added `POST /webhooks/whatsapp/signed`
- Verified raw request bytes before parsing JSON
- Rejected modified or incorrectly signed payloads
- Reused existing duplicate-message protection
- Added focused unit and API tests
- Updated the application version to `0.15.0`

### Concepts practised

- Webhook callback verification
- Environment-secret management
- Constant-time comparison
- HMAC-SHA256 authentication
- Raw-body request verification
- Request tamper detection
- Secure parsing order
- Plain-text HTTP responses
- Query aliases
- Authenticated idempotent webhook processing
- Resource-aware testing

### Key lesson

Webhook verification and webhook request authentication solve different problems.

The callback verification token proves that the webhook endpoint belongs to the application owner.

The HMAC signature proves that an incoming webhook payload was signed with the application secret and was not modified after signing.