# Changelog

All notable changes to the AI Engineering Product Lab are documented here.

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