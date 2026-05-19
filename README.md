# Enterprise Prompt

Enterprise Prompt is an AI-powered prompt engineering platform built with FastAPI and a lightweight SPA frontend.

It helps users analyze, refine, evaluate, and enhance prompts using configurable prompt engineering frameworks and multiple AI provider integrations.

## Features

- Prompt enhancement pipeline with analysis, selection, evaluation, refinement, and history storage
- Framework-driven prompt templates loaded from `config/frameworks.yaml`
- Support for multiple AI providers via a provider factory
- Real-time progress streaming through Server-Sent Events (SSE)
- Prompt history persistence using SQLite
- Easily extendable framework configuration with Jinja2 templates

## Getting Started

### Requirements

- Python 3.11+ (or compatible)
- `pip` package manager

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Run the App

```bash
uvicorn server:app --reload
```

By default, the app serves the SPA frontend at `http://localhost:8000/` and exposes API endpoints under `/api/`.

## Configuration

- `config/frameworks.yaml` — defines prompt engineering frameworks, enabled status, fields, and metadata
- `config/app_config.yaml` — application settings and server-related configuration
- `.env` — environment variables loaded by the application

## Project Structure

- `server.py` — FastAPI application entrypoint
- `src/engine` — prompt analysis, enhancement, evaluation, refinement, and selection logic
- `src/frameworks` — framework registry and prompt templates
- `src/providers` — AI provider integrations and provider factory
- `src/storage` — database and prompt history store
- `src/security` — prompt sanitizer and rate limiting
- `src/utils` — shared helpers, configuration loader, and logging setup
- `static/` — frontend assets
- `templates/` — SPA HTML shell

## API Endpoints

- `POST /api/enhance` — Enhance a prompt and stream progress updates
- `POST /api/analyze` — Analyze prompt structure and weaknesses
- `POST /api/evaluate` — Evaluate prompt quality
- `GET /api/frameworks` — List available frameworks
- `GET /api/frameworks/{framework_id}` — Get details for a specific framework
- `GET /api/history` — Retrieve saved prompt history

## Extending Frameworks

Add new prompt engineering frameworks by editing `config/frameworks.yaml` and adding a matching Jinja2 template file in `src/frameworks/templates/`.

## Notes

This repository is ideal for teams building internal prompt engineering tooling, AI prompt refinement services, or custom prompt quality dashboards.
