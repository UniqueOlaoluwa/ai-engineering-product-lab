# Changelog

All notable changes to the AI Engineering Product Lab are documented here.

## [0.12.0] — 2026-07-31

### Added

- Message pagination inside individual conversations
- `limit` and `offset` parameters for `GET /conversations/{session_id}`
- Total stored-message count per session
- Current-page message count
- Dedicated message-pagination query module
- Focused database and API pagination tests
- OpenAPI constraints for message-page values

### Changed

- Updated the API version to `0.12.0`
- Updated conversation retrieval to return paginated responses
- Expanded conversation-response metadata
- Reduced the maximum amount of conversation data returned by one request

### Validation and Performance

- Message limits must be between `1` and `100`
- Message offsets cannot be negative
- Unknown sessions continue to return structured `404` responses
- Offsets beyond the final message return successful empty pages
- Database retrieval uses parameterized `LIMIT` and `OFFSET`

## [0.11.0] — 2026-07-31

### Added

- Optional `search` query parameter for `GET /conversations`
- Case-insensitive session-ID searching
- Partial session-ID matching
- Filtered conversation counting
- Search combined with pagination
- Search normalization and validation
- Database and API integration tests for search
- Isolated project-local SQLite databases for API tests

### Changed

- Updated the API version to `0.11.0`
- Updated conversation listing to support optional filters
- Updated OpenAPI documentation with search constraints
- Reduced test impact on the development database
- Improved test reliability on low-memory Windows systems

### Validation and Safety

- Blank searches return structured `422` errors
- Searches longer than one hundred characters are rejected
- Search SQL remains parameterized
- Filtered totals use the same condition as filtered listings
- API tests no longer add records to the development database

## [0.10.0] — 2026-07-30

### Added

- `GET /conversations` endpoint
- Paginated conversation-session listing
- Conversation summary response models
- Distinct session counting
- Message-count aggregation per session
- First and latest activity timestamps
- Database indexes for session IDs and creation times
- Database and API pagination tests

### Changed

- Updated the API version to `0.10.0`
- Expanded the Conversations API group
- Ordered conversation summaries by recent activity
- Added reusable chat-test helper functions

### Validation and Performance

- Conversation limits must be between `1` and `100`
- Pagination offsets cannot be negative
- Invalid pagination values return structured `422` responses
- Session and creation-time indexes support more efficient lookups

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