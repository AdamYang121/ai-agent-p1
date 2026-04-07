# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Environment

- Python 3.14, virtualenv at `.venv/`
- Activate: `source .venv/bin/activate`
- Install packages: `.venv/bin/pip install <package>`

## Commands

```bash
# Run the main script
.venv/bin/python main.py

# Format code (Black is configured via PyCharm)
.venv/bin/black .
```

## Project

This is a new Python project intended for building a Claude agent. The entry point is `main.py`.