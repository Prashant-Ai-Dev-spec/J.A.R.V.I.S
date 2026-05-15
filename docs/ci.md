CI Integration

This repository includes a GitHub Actions workflow (.github/workflows/ci.yml) that:
- installs dependencies
- starts the MCP connector (with JARVIS_MCP_TOKEN from secrets)
- runs the test suite

To run locally, set the environment variable JARVIS_MCP_TOKEN and run:

python -m uvicorn backend.mcp.connector:app --host 127.0.0.1 --port 8000
python testing/run_tests.py
