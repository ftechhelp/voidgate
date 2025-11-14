# Voidgate Project - AI Assistant Instructions

## Project Overview
Voidgate is a minimal HTTP API server for executing commands and scripts in isolated environments. The entire application is a single Python file (`api.py`) with no external dependencies beyond Python standard library.

## Architecture
- **Single-file application**: All code in `api.py`
- **HTTP server**: Uses Python's built-in `http.server` and `socketserver`
- **No framework**: Deliberately lightweight with manual request/response handling
- **Stateless**: Each request is independent, no session management

## Configuration
- **API Password**: Set via `VOIDGATE_PASSWORD` environment variable (default: `"playground_voidgate"`)
- **Host IP**: Set via `VOIDGATE_HOST` environment variable (default: `"172.17.0.1"`)
- Example: `VOIDGATE_PASSWORD=secret VOIDGATE_HOST=127.0.0.1 python3 api.py`

## API Endpoints
- `POST /execute` - Execute shell commands with 30s timeout
- `POST /run_script` - Execute scripts from absolute paths with optional args and working directory
- `GET /health` - Simple health check returning `{"status": "healthy"}`

## Security Model
- **Password authentication**: All requests require `password` field in JSON body
- **Design intention**: For isolated/controlled environments only, never internet-exposed
- Default bind address `172.17.0.1` is Docker bridge interface

## Request/Response Patterns
All endpoints expect/return JSON. Example execute request:
```json
{"password": "playground_voidgate", "command": "ls -la"}
```

Example run_script request:
```json
{
  "password": "playground_voidgate",
  "script_path": "/absolute/path/to/script.sh",
  "args": ["--flag", "value"],
  "working_dir": "/absolute/path/to/dir"
}
```

## Key Implementation Details
- **Timeouts**: All command/script executions have 30s timeout (subprocess.TimeoutExpired)
- **Path validation**: `run_script` requires absolute paths for `script_path` and `working_dir`
- **Error handling**: Returns appropriate HTTP status codes (400, 401, 403, 404, 408, 500)
- **Logging**: Custom `log_message()` override suppresses verbose request logs
- **Text mode**: All subprocess output captured as text (not bytes)

## Development Workflow
- **Run server locally**: `python3 api.py` (starts on `http://172.17.0.1:5000` by default)
- **Custom configuration**: `VOIDGATE_PASSWORD=mypass VOIDGATE_HOST=127.0.0.1 python3 api.py`
- **Run tests**: `python3 test_api.py` or `python3 -m unittest test_api.py -v`
- **Docker build**: `docker build -t voidgate .`
- **Docker run**: `docker run -p 5000:5000 -e VOIDGATE_PASSWORD=secret voidgate`
- **Docker Compose**: `docker-compose up -d` (uses `VOIDGATE_PASSWORD` from environment or defaults)
- **No dependencies**: Pure Python 3 stdlib, no requirements.txt or virtual environment needed

## Code Conventions
- Shebang line: `#!/usr/bin/env python3` for direct execution
- Response format: Always JSON via `send_json_response(data, status_code)` helper
- Command execution: Use `subprocess.run()` with `shell=True` for execute, direct array for run_script
- Error responses: Include `"error"` key in JSON body
- Environment variables: Use `VOIDGATE_*` prefix for all configuration

## When Modifying Code
- Keep single-file structure (no splitting into modules)
- Preserve environment variable configuration pattern (`VOIDGATE_*` prefix)
- Preserve 30s timeout unless explicitly requested to change
- All paths in `run_script` must remain absolute (security measure)
- Keep warning messages on startup about security risks
