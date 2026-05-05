@echo off
echo Starting all services...
start "Docker" cmd /k "docker compose up"
timeout /t 10
start "Server" cmd /k "uvicorn app.main:app --reload"
start "HTTP" cmd /k "python -m http.server 5500"
start "Ollama" cmd /k "ollama serve"
echo All services started!