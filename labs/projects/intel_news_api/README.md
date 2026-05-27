# Intel Mobile Status API (LAB-003)

Lekkie API FastAPI wystawiajace status watchera LAB-002 na bazie plikow runtime.

## Run

powershell
& .\.venv\Scripts\python.exe -m uvicorn labs.projects.intel_news_api.app:app --host 127.0.0.1 --port 8890

## Endpoints

- GET /health
- GET /api/intel/status
- GET /api/intel/state
- GET /api/intel/diff

## Data sources

- labs/projects/intel_news_watcher/runtime/state.json
- labs/projects/intel_news_watcher/runtime/latest_diff.json
