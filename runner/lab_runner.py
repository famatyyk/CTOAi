#!/usr/bin/env python3
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import yaml

ROOT = Path(__file__).resolve().parent.parent
LAB_TASKS_FILE = ROOT / "labs" / "tasks" / "mythibia-projects.yaml"
LAB_LOG_FILE = ROOT / "logs" / "lab-runner.log"


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def log(msg: str) -> None:
    LAB_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    line = f"[{now_iso()}] {msg}"
    with LAB_LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(line + "\n")
    print(line)


def load_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Missing file: {path}")
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Invalid YAML in {path}")
    return data


def save_yaml(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        yaml.safe_dump(payload, f, sort_keys=False, allow_unicode=False)
        f.flush()
        os.fsync(f.fileno())
    tmp.replace(path)


def write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def generate_news_scraper(project_dir: Path, target_url: str) -> List[str]:
    files = []
    main_py = f'''#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

TARGET_URL = "{target_url}"
OUT_FILE = Path("data/latest_news.json")
HEADERS = {{
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,pl;q=0.8",
    "Cache-Control": "no-cache",
}}


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def parse_news(html: str):
    soup = BeautifulSoup(html, "html.parser")
    candidates = soup.select("article, .news-item, .post, .entry, li")
    out = []

    for node in candidates:
        a = node.select_one("a[href]")
        if not a:
            continue
        title = (a.get_text() or "").strip()
        href = (a.get("href") or "").strip()
        if not title or not href:
            continue
        if href.startswith("/"):
            href = "https://mythibia.online" + href
        out.append({{"title": title, "url": href}})

    uniq = []
    seen = set()
    for item in out:
        key = item["url"]
        if key in seen:
            continue
        seen.add(key)
        uniq.append(item)

    return uniq[:50]


def main() -> None:
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    r = requests.get(TARGET_URL, headers=HEADERS, timeout=20)
    if r.status_code == 403 and not TARGET_URL.endswith("/"):
        r = requests.get(TARGET_URL + "/", headers=HEADERS, timeout=20)
    if r.status_code >= 400:
        payload = {{
            "generated_at": now_iso(),
            "target": TARGET_URL,
            "count": 0,
            "items": [],
            "fetch_status": r.status_code,
            "fetch_error": f"HTTP {{r.status_code}} from source",
        }}
        OUT_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Source blocked with status {{r.status_code}}; wrote empty payload to {{OUT_FILE}}")
        return

    r.raise_for_status()
    items = parse_news(r.text)
    payload = {{
        "generated_at": now_iso(),
        "target": TARGET_URL,
        "count": len(items),
        "items": items,
    }}
    OUT_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved {{len(items)}} items to {{OUT_FILE}}")


if __name__ == "__main__":
    main()
'''
    req = "requests>=2.31.0\nbeautifulsoup4>=4.12.0\n"

    write_file(project_dir / "main.py", main_py)
    write_file(project_dir / "requirements.txt", req)
    files.extend(["main.py", "requirements.txt"])
    return files


def generate_news_watcher(project_dir: Path, target_url: str) -> List[str]:
    files = []
    watcher_py = f'''#!/usr/bin/env python3
import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
SCRAPER_PATH = PROJECT_ROOT.parent / "mythibia_news_scraper" / "main.py"
STATE_FILE = PROJECT_ROOT / "data" / "watcher_state.json"
LOG_FILE = PROJECT_ROOT / "logs" / "watcher.log"


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def log(msg: str) -> None:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(f"[{{now_iso()}}] {{msg}}\\n")


def load_state() -> dict:
    if not STATE_FILE.exists():
        return {{"seen": []}}
    return json.loads(STATE_FILE.read_text(encoding="utf-8"))


def save_state(data: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def run_once() -> None:
    res = subprocess.run(["python3", str(SCRAPER_PATH)], capture_output=True, text=True)
    if res.returncode != 0:
        log(f"scraper failed: {{res.stderr[-500:]}}")
        return

    latest = PROJECT_ROOT.parent / "mythibia_news_scraper" / "data" / "latest_news.json"
    if not latest.exists():
        log("latest_news.json missing")
        return

    payload = json.loads(latest.read_text(encoding="utf-8"))
    items = payload.get("items", [])

    state = load_state()
    seen = set(state.get("seen", []))
    new_items = [i for i in items if i.get("url") not in seen]

    if new_items:
        for i in new_items[:5]:
            log(f"NEW: {{i.get('title')}} | {{i.get('url')}}")

    for i in items:
        if i.get("url"):
            seen.add(i["url"])

    state["seen"] = list(seen)[-500:]
    state["updated_at"] = now_iso()
    save_state(state)


def main() -> None:
    while True:
        run_once()
        time.sleep(120)


if __name__ == "__main__":
    main()
'''
    write_file(project_dir / "watcher.py", watcher_py)
    files.append("watcher.py")
    return files


def generate_news_api(project_dir: Path, target_url: str) -> List[str]:
    files = []
    app_py = f'''#!/usr/bin/env python3
import json
from pathlib import Path

from fastapi import FastAPI

app = FastAPI(title="Mythibia News API")
SCRAPER_OUT = Path(__file__).resolve().parent.parent / "mythibia_news_scraper" / "data" / "latest_news.json"


@app.get("/health")
def health() -> dict:
    return {{"ok": True, "target": "{target_url}"}}


@app.get("/news")
def news() -> dict:
    if not SCRAPER_OUT.exists():
        return {{"ok": False, "detail": "No data yet"}}
    return json.loads(SCRAPER_OUT.read_text(encoding="utf-8"))
'''
    req = "fastapi>=0.115.0\nuvicorn>=0.30.0\n"
    run_sh = "python3 -m uvicorn app:app --host 0.0.0.0 --port 8890\n"

    write_file(project_dir / "app.py", app_py)
    write_file(project_dir / "requirements.txt", req)
    write_file(project_dir / "run.sh", run_sh)
    files.extend(["app.py", "requirements.txt", "run.sh"])
    return files


def run_smoke(project_dir: Path) -> None:
    for py in project_dir.rglob("*.py"):
        subprocess.run(["python3", "-m", "py_compile", str(py)], check=True)


def process_task(task: Dict[str, Any]) -> Dict[str, Any]:
    task_id = str(task.get("id"))
    template = str(task.get("template", ""))
    project_dir = ROOT / str(task.get("project_folder"))
    target_url = str(task.get("target_url", "https://mythibia.online/news"))

    log(f"agent-brain: planning {task_id} ({template})")
    task["status"] = "IN_PROGRESS"
    task["updated_at"] = now_iso()

    generated: List[str] = []
    if template == "news_scraper":
        generated = generate_news_scraper(project_dir, target_url)
    elif template == "news_watcher":
        generated = generate_news_watcher(project_dir, target_url)
    elif template == "news_api":
        generated = generate_news_api(project_dir, target_url)
    else:
        raise ValueError(f"Unknown template: {template}")

    run_smoke(project_dir)

    task["status"] = "GENERATED"
    task["updated_at"] = now_iso()
    task["generated_files"] = generated
    task["project_abs"] = str(project_dir)
    log(f"agent-builder: generated {task_id} in {project_dir}")

    task["status"] = "READY"
    task["updated_at"] = now_iso()
    return task


def main() -> None:
    data = load_yaml(LAB_TASKS_FILE)
    tasks = data.get("tasks", [])
    if not isinstance(tasks, list):
        raise ValueError("Invalid tasks list")

    target = None
    for t in tasks:
        if str(t.get("status", "NEW")) == "NEW":
            target = t
            break

    if target is None:
        log("agent-brain: no NEW lab tasks")
        return

    try:
        process_task(target)
        save_yaml(LAB_TASKS_FILE, data)
        log(f"agent-brain: task {target.get('id')} is READY")
    except Exception as ex:
        target["status"] = "FAILED"
        target["updated_at"] = now_iso()
        target["error"] = str(ex)
        save_yaml(LAB_TASKS_FILE, data)
        log(f"agent-brain: task {target.get('id')} FAILED: {ex}")
        raise


if __name__ == "__main__":
    main()
