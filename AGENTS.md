# AGENTS.md — openlink Development Guide

## Build & Run Commands

### FastAPI Server
```bash
cd backend
uv sync
uv run openlink -dir /path/to/workspace -port 39527

# Or directly
uv run python -m app.main -dir /path/to/workspace -port 39527
```

### Chrome Extension
```bash
cd extension
npm install
npm run build    # outputs to extension/dist/
npm run dev      # watch mode
```

### Vue Frontend
```bash
cd frontend
npm install
npm run dev      # dev server (port 5173)
npm run build    # production build → frontend/dist/
```

### Testing
```bash
cd backend
uv run pytest
```

### Verification
```bash
# Check server health
curl http://127.0.0.1:39527/health

# List tools (with auth)
TOKEN=$(python -c "import json; print(json.load(open('$HOME/.openlink/settings.json'))['token'])")
curl http://127.0.0.1:39527/tools -H "Authorization: Bearer $TOKEN"
```

### Scripts
```bash
./scripts/build.sh all          # Build extension + frontend
./scripts/deploy-extension.sh   # Package extension for deployment
```

## Code Style Guidelines

### Python (Backend)
- Follow PEP 8
- Use `from __future__ import annotations` for forward references
- Type hints on all function signatures
- Abstract base classes for tool definitions (`BaseTool`)
- `async def` for I/O-heavy endpoints
- Pydantic models with `model_validator` for field normalization
- Use `os.path.realpath()` for symlink resolution in security checks

### TypeScript (Extension)
- Strict mode enabled
- Use `interface` for data shapes, `type` for unions
- Async/await for all API calls
- Match existing code style in `extension/src/content/index.ts`
- No React — content script uses vanilla DOM manipulation

### Vue 3 (Frontend)
- Composition API with `<script setup lang="ts">`
- Pinia stores with composable pattern
- Scoped CSS with CSS variables from dark theme
- Lazy-loaded route components

### Naming Conventions
- **Python**: `snake_case` for functions/variables, `PascalCase` for classes
- **Python files**: `snake_case.py`
- **TypeScript**: `camelCase` for variables/functions, `PascalCase` for types/components
- **Vue files**: `PascalCase.vue` for components

### Error Handling
- Backend: Return `ToolResult` with `status="error"` and descriptive error message
- Extension: surface errors in tool card UI
- Never expose internal paths or stack traces to client

### Security Patterns
- Always validate file paths with `safe_path()` from `core/security/sandbox.py`
- Always resolve symlinks before path validation
- Use `is_dangerous_command()` before shell execution
- Use `secrets.compare_digest()` for token comparison
- SSRF protection in `web_fetch` — resolve host and check private IP ranges

### Git & Commits
- Keep commits focused on single concerns
- Write clear commit messages explaining "why" not just "what"
- No commits unless explicitly requested by user

## Architecture Notes
- Server uses FastAPI with lifespan context manager for startup/shutdown
- CORS enabled for all origins (required for browser extension)
- Tool execution uses `asyncio.wait_for()` with timeout
- Skills system loads `SKILL.md` files from 7 directories, deduplicates by name
- Vue frontend mounted as static files at `/app/` with SPA fallback middleware
