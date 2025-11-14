# Voidgate

A minimal HTTP API server for executing commands and scripts in isolated environments. Built with zero external dependencies using only Python's standard library.

## ⚠️ Security Warning

**This API allows arbitrary command execution and should ONLY be used in isolated, controlled environments. Never expose this to the internet.**

## Features

- **Lightweight**: Single Python file, no external dependencies
- **Command Execution**: Execute shell commands via HTTP API
- **Script Execution**: Run scripts from absolute paths with arguments
- **Configurable**: Environment variable configuration for password and bind address
- **Health Check**: Simple health check endpoint for monitoring

## Quick Start

### Local Development

```bash
# Run with defaults (binds to 172.17.0.1:5000)
python3 api.py

# Run with custom configuration
VOIDGATE_PASSWORD=mysecret VOIDGATE_HOST=127.0.0.1 python3 api.py
```

### Docker

```bash
# Build image
docker build -t voidgate .

# Run container
docker run -p 5000:5000 -e VOIDGATE_PASSWORD=secret voidgate

# Or use docker-compose
VOIDGATE_PASSWORD=secret docker-compose up -d
```

## Configuration

Configure via environment variables:

- `VOIDGATE_PASSWORD` - API authentication password (default: `playground_voidgate`)
- `VOIDGATE_HOST` - Host IP to bind to (default: `172.17.0.1`)

## API Endpoints

### Health Check

```bash
curl http://127.0.0.1:5000/health
```

Response:
```json
{"status": "healthy"}
```

### Execute Command

Execute a shell command with 30-second timeout.

```bash
curl -X POST http://127.0.0.1:5000/execute \
  -H "Content-Type: application/json" \
  -d '{
    "password": "playground_voidgate",
    "command": "ls -la"
  }'
```

Response:
```json
{
  "stdout": "...",
  "stderr": "...",
  "return_code": 0,
  "success": true
}
```

### Run Script

Execute a script from an absolute path with optional arguments and working directory.

```bash
curl -X POST http://127.0.0.1:5000/run_script \
  -H "Content-Type: application/json" \
  -d '{
    "password": "playground_voidgate",
    "script_path": "/absolute/path/to/script.sh",
    "args": ["arg1", "arg2"],
    "working_dir": "/absolute/path/to/workdir"
  }'
```

Response:
```json
{
  "stdout": "...",
  "stderr": "...",
  "return_code": 0,
  "success": true,
  "script_path": "/absolute/path/to/script.sh",
  "args": ["arg1", "arg2"],
  "working_dir": "/absolute/path/to/workdir"
}
```

## Request Parameters

### `/execute`
- `password` (required): Authentication password
- `command` (required): Shell command to execute

### `/run_script`
- `password` (required): Authentication password
- `script_path` (required): Absolute path to script file
- `args` (optional): Array of arguments to pass to script
- `working_dir` (optional): Absolute path for script working directory

## Error Responses

All errors return JSON with an `error` field:

- `400 Bad Request` - Invalid request (missing parameters, invalid JSON, relative paths)
- `401 Unauthorized` - Invalid password
- `403 Forbidden` - Script file not readable
- `404 Not Found` - Endpoint or script file not found
- `408 Request Timeout` - Command/script exceeded 30-second timeout
- `500 Internal Server Error` - Server error

Example error:
```json
{"error": "Invalid password"}
```

## Development

### Requirements

- Python 3.6 or higher
- No external dependencies

### Running Tests

```bash
# Run all tests
python3 test_api.py

# Run with verbose output
python3 -m unittest test_api.py -v
```

The test suite includes 20 tests covering:
- All API endpoints
- Authentication and authorization
- Error handling and validation
- Command and script execution
- Path validation

## Use Cases

Voidgate is designed for a specific use case: **running commands on the host machine from Docker containers**.

### Primary Use Case

When you run everything on your server as Docker containers in segregated networks, you sometimes need containers to execute commands on the host system. Voidgate provides this capability by running on the host and exposing an API that containers can call.

**Deployment Pattern:**
- **Production/Server**: Run `api.py` directly on the host system (not in Docker)
- **Local Development**: Run in Docker to test services that will use it
- **Default IP (`172.17.0.1`)**: This is typically the Docker bridge gateway IP, allowing containers to access the API on the host

### Security Considerations

The API must remain isolated from the internet. Ensure:
- Bind to Docker bridge interface (`172.17.0.1`) or localhost only
- Use firewall rules to block external access
- Use a strong password via `VOIDGATE_PASSWORD`
- Only expose to trusted container networks

### Additional Use Cases

- CI/CD pipeline automation
- Development environment orchestration
- Isolated command execution for testing

## Architecture

- **Single-file application**: All code in `api.py`
- **Built-in HTTP server**: Uses `http.server` and `socketserver` from Python stdlib
- **Stateless**: No session management or persistent state
- **Synchronous**: Requests block until command/script completes (30s max)

## License

This project is provided as-is for use in isolated, controlled environments only.
