JARVIS Cowork — Documentation

Overview
- Goal: reach feature parity with Claude Cowork. This docs folder will host user and developer guides, API references, and deployment steps.

Running tests
- From project root run: python testing\run_tests.py

Starting MCP connector
- python -m uvicorn backend.mcp.connector:app --host 127.0.0.1 --port 8000

Contributing
- Follow the plan in session-state/plan.md and update todos via the Copilot CLI workflow.
