# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

openlink is a browser-local proxy that enables web-based AI assistants (Gemini/ChatGPT/DeepSeek etc.) to access the local filesystem through a sandboxed FastAPI server and Chrome extension.

**Architecture**: Three-component system:
1. **FastAPI Server** (`backend/app/main.py`): HTTP server that executes filesystem operations within a sandboxed directory
2. **Chrome Extension** (`extension/src/content/index.ts`): Content script that intercepts AI tool calls from web pages, proxies them to the local server, and provides input completion UI
3. **Vue 3 Dashboard** (`frontend/src/`): Web-based management panel served at `/app/`

## Development Commands

### Running the Server

```bash
cd backend
uv sync
uv run openlink -dir /path/to/workspace -port 39527 -timeout 60
```

### Building the Extension

```bash
cd extension
npm install
npm run build   # outputs to extension/dist/
```

### Building the Frontend

```bash
cd frontend
npm install
npm run dev     # dev server with hot reload
npm run build   # production build, served by FastAPI at /app/
```

### Testing the Server

```bash
# Check server health
curl http://127.0.0.1:39527/health

# List available skills
curl http://127.0.0.1:39527/skills -H "Authorization: Bearer <token>"

# Test command execution
curl -X POST http://127.0.0.1:39527/exec \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"name":"exec_cmd","args":{"command":"ls -la"}}'
```

### Installing the Extension

1. Build first: `cd extension && npm run build`
2. Open Chrome: `chrome://extensions/`
3. Enable "Developer mode"
4. Click "Load unpacked"
5. Select the `extension/dist/` directory

## Code Architecture

### Request Flow

```
Web AI (Gemini/ChatGPT/DeepSeek/etc.)
  ↓ outputs <tool> tags in response
content script (extension/src/content/index.ts)
  ↓ MutationObserver detects tool tags, renders card UI
  ↓ HTTP POST to localhost:39527/exec (via background fetch)
FastAPI Server (backend/app/main.py)
  ↓ validates & sanitizes
Executor (backend/app/executor/executor.py)
  ↓ executes with sandbox
Security Layer (backend/app/core/security/sandbox.py)
  ↓ path validation & command filtering
Local Filesystem
```

### Key Components

**backend/app/schemas/types.py**: Core data structures
- `ToolRequest`: Incoming tool call from browser (name, args, optional arguments alias)
- `ToolResponse`: Execution result (status, output, error, stopStream)
- `AppConfig`: Server configuration (root_dir, port, timeout, token)

**backend/app/core/security/sandbox.py**: Security enforcement
- `safe_path()`: Validates all file paths stay within RootDir via `os.path.realpath()`
- `is_dangerous_command()`: Blocks dangerous commands (rm -rf, sudo, curl, wget, etc.)

**backend/app/core/security/auth.py**: Token-based auth
- `load_or_create_token()`: Reads `~/.openlink/settings.json`, generates 32-byte hex token if missing
- `verify_token()`: FastAPI dependency using HTTPBearer, constant-time comparison via `secrets.compare_digest()`

**backend/app/executor/executor.py**: Tool execution dispatcher
- All operations run with asyncio timeout (default 60s)
- Identity reminder injected every call, full init prompt every 20 calls
- Case-insensitive tool lookup

**backend/app/tools/**: Individual tool implementations
- `edit.py`: 10-strategy string replacement cascade (most complex, ~330 lines)
- Other tools: exec_cmd, list_dir, read_file, write_file, glob, grep, web_fetch, question, skill, todo_write

**backend/app/skills/loader.py**: Skills loader
- Scans 7 directories for SKILL.md files, parses YAML frontmatter

**backend/app/api/**: FastAPI endpoints
- `GET /health`: Server status and version
- `GET /config`: Current configuration
- `GET /prompt`: Init prompt with system info and skills list
- `GET /skills`: Available skills (name + description)
- `GET /tools`: Registered tools with parameters
- `GET /files?q=`: File listing under RootDir (max 50, skips .git/node_modules)
- `POST /exec`: Execute tool requests
- `POST /auth`: Validate token
- CORS enabled for all origins

**extension/src/content/index.ts**: Main content script
- `getSiteConfig()`: Per-site selectors for editor, send button, fill method
- `startDOMObserver()`: MutationObserver with debounce (800ms) + maxWait (3000ms) for tool detection
- `renderToolCard()`: Renders manual execution UI card above each detected tool call
- `fillAndSend()`: Fills editor and optionally auto-sends with configurable delay
- `attachInputListener()`: Slash command (`/`) and `@` file completion on input events
- `showPickerPopup()`: Keyboard-navigable dropdown for skill/file selection
- `replaceTokenInEditor()`: Cross-platform token replacement (value/execCommand/prosemirror/paste)

**frontend/src/**: Vue 3 SPA
- Pages: Dashboard, Connection, ToolConsole, FileBrowser, SkillsView, PromptViewer, Settings
- Stores (Pinia): connection, tools, skills
- API client: Axios with Bearer token interceptor

### Supported AI Platforms

| Platform | fillMethod | useObserver | Notes |
|----------|-----------|-------------|-------|
| Google AI Studio | value | true | Recommended; writes to System Instructions |
| Google Gemini | execCommand | true | |
| ChatGPT | prosemirror | true | |
| 通义千问 (Qwen) | value | true | |
| DeepSeek | paste | false | Uses injected.js |
| Kimi | execCommand | false | |
| Mistral | execCommand | false | |
| Perplexity | execCommand | false | |
| Arena.ai | value | true | |
| OpenRouter | value | false | |
| Grok | value | false | |
| GitHub Copilot | value | false | |
| t3.chat | value | false | |
| z.ai | value | false | |

## Module Information

- **Backend**: Python >= 3.12, FastAPI + Pydantic + httpx + uvicorn
- **Package Manager**: uv
- **Frontend**: Vue 3 + Pinia + Vue Router + Axios, built with Vite
- **Extension**: TypeScript, Manifest V3, built with Vite
