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