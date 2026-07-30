# Changelog

All notable changes to the AI Engineering Product Lab are documented here.

## [0.9.0] — 2026-07-30

### Added

- Conversation deletion database function
- `DELETE /conversations/{session_id}` endpoint
- Conversation-deletion response model
- Deleted-message count reporting
- Database tests for session deletion
- API integration tests for deletion behaviour

### Changed

- Updated the API version to `0.9.0`
- Expanded the Conversations API group
- Updated database documentation to include data removal
- Improved data lifecycle support

### Validation and Safety

- Blank session IDs are rejected by the database layer
- Unknown sessions return a structured `404`
- Deleting one session does not affect another session
- SQL deletion uses a parameterized query

## [0.8.0] — 2026-07-30

### Added

- Configurable `history_limit` field for chat requests
- Per-request conversation-memory controls
- Support for disabling memory with `history_limit: 0`
- Validation for memory limits between zero and twenty
- Boundary-value API tests
- OpenAPI documentation for memory constraints

### Changed

- Updated the API version to `0.8.0`
- Updated `/chat` to use the requested conversation-history limit
- Expanded API integration tests for memory behaviour
- Documented the difference between prompt memory and permanent storage

### Validation

- Negative memory limits return `422`
- Limits above twenty return `422`
- The maximum allowed value of twenty is accepted
- Disabling memory still saves the new exchange

## [0.7.0] — 2026-07-30

### Added

- Conversation-aware chat responses
- Retrieval of previous messages before prompt construction
- Recent-message selection with a five-exchange limit
- Conversation-context formatting utilities
- Session-isolation tests
- Multi-turn API integration tests
- Unique test session identifiers

### Changed

- Updated the API version to `0.7.0`
- Updated `/chat` to include previous session context
- Improved API tests to avoid data left by earlier test runs
- Stored only original user messages instead of formatted prompt context

### Security and Privacy

- Kept conversation memory isolated by session ID
- Prevented one session from inheriting another session's history
- Limited the amount of stored history inserted into prompts

## [0.6.0] — 2026-07-30

### Added

- Root API-information endpoint
- API metadata and endpoint grouping
- SQLite conversation storage
- Conversation-history retrieval endpoint
- Request-ID middleware
- Structured request logging
- Centralized HTTP exception handling
- Centralized request-validation error handling
- Standard error-response structure
- Database and middleware test coverage
- HTTPX2 test dependency

### Changed

- Updated the API version to `0.6.0`
- Improved Swagger and OpenAPI documentation
- Improved request tracing and error correlation
- Improved SQLite connection cleanup on Windows
- Expanded README architecture and endpoint documentation

### Security

- Validated client-supplied request IDs
- Replaced unsafe request IDs with generated UUIDs
- Used parameterized SQLite queries
- Kept environment files and local databases out of Git

## [0.1.0] — Initial Foundation

### Added

- Project structure
- Role-based prompt builder
- JSON prompt templates
- Environment configuration
- Provider interface
- Mock provider
- Custom application errors
- Automated unit tests