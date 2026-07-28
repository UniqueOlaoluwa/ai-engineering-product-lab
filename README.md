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


## Current Architecture

```text
Private Environment Configuration
  ↓
Settings Loader
  ↓
Provider Factory
  ↓
Safe Application Startup
  ↓
Command-Line Interface
  ↓
Role Normalization and Prompt Builder
  ↓
Cached JSON Configuration Loader
  ↓
Provider Interface
  ↓
Mock Model Provider
  ↓
Assistant Response
```

The project currently separates:

- environment configuration in `.env`
- public configuration examples in `.env.example`
- settings loading in `app/config.py`
- provider creation in `app/providers/factory.py`
- safe startup and interaction flow in `app/main.py`
- prompt-building logic in `app/prompt_builder.py`
- custom application errors in `app/exceptions.py`
- JSON loading and validation in `app/templates.py`
- provider interface in `app/providers/base.py`
- mock-provider behaviour in `app/providers/mock.py`
- assistant-role configuration in `data/prompt_templates.json`
```

The project currently separates:

- user-interface logic in `app/main.py`
- prompt-building logic in `app/prompt_builder.py`
- JSON loading and validation in `app/templates.py`
- assistant configuration in `data/prompt_templates.json`

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