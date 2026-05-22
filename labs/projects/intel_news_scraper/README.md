# Intel News Scraper (LAB-001)

This project fetches and parses news links from:
- https://tibiantis.online/news

## Run

```powershell
& .\.venv\Scripts\python.exe -m labs.projects.intel_news_scraper.scraper --print
```

## Output files

- `labs/projects/intel_news_scraper/runtime/latest.json`
- `labs/projects/intel_news_scraper/runtime/archive/news_*.json`
