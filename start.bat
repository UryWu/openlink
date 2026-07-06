@echo off
title openlink

echo ========================================
echo   openlink
echo ========================================
echo.

:: 1. Build extension (required - intercepts AI tool calls from web pages)
echo [1/4] Building Chrome extension...
pushd "%~dp0extension"
if exist "node_modules\" (
    echo   node_modules found, skipping install
) else (
    echo   installing npm dependencies...
    call npm install
)
call npm run build
if %ERRORLEVEL% neq 0 (
    echo WARNING: extension build failed
) else (
    echo   extension built -^> extension\dist\
)
popd

:: 2. Build frontend (optional - dashboard at /app/)
echo.
echo [2/4] Building dashboard...
pushd "%~dp0frontend"
if exist "node_modules\" (
    echo   node_modules found, skipping install
) else (
    echo   installing npm dependencies...
    call npm install
)
call npm run build
if %ERRORLEVEL% neq 0 (
    echo WARNING: dashboard build failed, /app/ will not be available
) else (
    echo   dashboard built -^> frontend\dist\
)
popd

:: 3. Install backend deps
echo.
echo [3/4] Installing backend dependencies...
pushd "%~dp0backend"
uv sync
if %ERRORLEVEL% neq 0 (
    echo ERROR: uv sync failed
    pause
    exit /b 1
)
popd

:: 4. Start server
echo.
echo [4/4] Starting server on port 39527 ...
echo.
echo   API:              http://127.0.0.1:39527/health
echo   Dashboard:        http://127.0.0.1:39527/app/
echo.
echo   Load extension:   chrome://extensions/ -^> select extension\dist\
echo.
pushd "%~dp0backend"
uv run python -m app.main -dir "%~dp0." -port 39527
popd

pause
