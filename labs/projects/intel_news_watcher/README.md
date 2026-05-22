# Intel News Watcher (LAB-002)

Watcher uruchamia scraper LAB-001, porownuje aktualny snapshot z poprzednim stanem i emituje diff.

## Run once

powershell
& .\.venv\Scripts\python.exe -m labs.projects.intel_news_watcher.watcher --print-json

## Run as daemon

powershell
& .\.venv\Scripts\python.exe -m labs.projects.intel_news_watcher.watcher --daemon --interval 300

## Runtime outputs

- labs/projects/intel_news_watcher/runtime/state.json
- labs/projects/intel_news_watcher/runtime/latest_diff.json
- labs/projects/intel_news_watcher/runtime/archive/diff_*.json
