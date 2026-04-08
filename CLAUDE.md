# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Environment

- Python 3.14, virtualenv at `.venv/`
- Install packages: `.venv/bin/pip install <package>`
- Config via `.env` file (loaded by pydantic-settings): `ANTHROPIC_API_KEY`, `GC_PASSWORD`, `SECRET_KEY`, `DATABASE_URL`

## Commands

```bash
# Run dev server (auto-reload)
.venv/bin/uvicorn main:app --reload

# Run via Docker
docker compose up

# Format code
.venv/bin/black .
```

## Architecture

This is a **FastAPI** bathroom remodel estimator for a general contractor (GC) in Seattle. It uses Jinja2 HTML templates (no frontend framework), async SQLAlchemy with SQLite (`remodel.db`), and the Anthropic API.

**Two user types with separate flows:**

- **GC** (`/gc/*`) — password-protected (cookie session stored in `_sessions` set in memory). GC creates projects, reviews intake, generates/edits estimates, sends quotes, downloads PDFs.
- **Homeowner** (`/project/<token>/*`) — token-based access (no login). Fills out a questionnaire, views quotes, and accepts/rejects.

**Project lifecycle:** `intake` → `estimated` → `reviewed` → `sent` → `accepted`/`rejected`

**Key modules:**

- `app/models.py` — SQLAlchemy models: `Project`, `ProjectIntake`, `Estimate`, `Message`
- `app/services/estimator.py` — pure-Python estimation engine; reads pricing constants from `pricing/seattle_pricing.py` and builds line items split into labor (no tax) vs. material (taxed) categories
- `app/services/claude_service.py` — three Claude integrations: scope extraction from freetext description → structured JSON, Q&A with topic auto-tagging, PDF cover letter generation
- `app/services/pdf_service.py` — ReportLab PDF generation for quote download
- `app/routers/messages.py` — homeowner Q&A thread; Claude auto-answers, GC can override

**Pricing** lives in `pricing/seattle_pricing.py` as a `FinishLevel` enum (`budget`/`mid`/`luxury`) with dicts keyed by finish level. To adjust pricing, edit that file — the estimator engine reads from it directly.