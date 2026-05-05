@echo off
echo Stopping all services...
docker compose down
taskkill /f /im ollama.exe 2>nul
echo Done! All services stopped.
pause