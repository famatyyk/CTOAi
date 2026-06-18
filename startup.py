#!/usr/bin/env python3
"""
CTOAi One-Click Startup — uruchamia wszystko automatycznie

Uruchamia:
1. Docker model server (localhost:11434)
2. CTOAi services (docker-compose)
3. Otwiera VSCode z chatem AI
"""

import subprocess
import time
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)


def run_cmd(cmd, desc, background=False):
    """Run command and log output."""
    print(f"\n{'='*60}")
    print(f"[startup] {desc}")
    print(f"{'='*60}")
    
    try:
        if background:
            print(f"[startup] Starting in background: {' '.join(cmd)}")
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(2)  # Give it time to start
        else:
            print(f"[startup] Running: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=False)
            if result.returncode != 0:
                print(f"[startup] ✗ FAILED: {desc}")
                return False
        
        print(f"[startup] ✓ OK: {desc}")
        return True
    except Exception as e:
        print(f"[startup] ✗ ERROR: {e}")
        return False


def main():
    print("""
╔════════════════════════════════════════════════════════════╗
║          CTOAi One-Click Startup                          ║
║     All-in-one: Model + Services + VSCode                ║
╚════════════════════════════════════════════════════════════╝
    """)

    # Step 1: Check model is pulled
    print("\n[startup] Checking if model is cached...")
    result = subprocess.run(
        ["docker", "model", "ls"],
        capture_output=True,
        text=True
    )
    
    if "Qwen" not in result.stdout and "qwen" not in result.stdout:
        print("[startup] Model not found. Pulling...")
        if not run_cmd(
            ["docker", "model", "pull", "hf.co/bartowski/Qwen2.5-Coder-1.5B-Instruct-GGUF"],
            "Pull Qwen2.5-Coder model (~1GB, one-time)"
        ):
            return 1
    else:
        print("[startup] ✓ Model already cached")

    # Step 2: Start model server
    print("\n[startup] Starting local model server on localhost:11434...")
    run_cmd(
        ["docker", "model", "run", "hf.co/bartowski/Qwen2.5-Coder-1.5B-Instruct-GGUF"],
        "Start Docker Model Runner (localhost:11434)",
        background=True
    )
    
    # Wait for model to be ready
    print("[startup] Waiting for model server to start (30 seconds)...")
    for i in range(30):
        try:
            result = subprocess.run(
                ["curl", "-s", "http://localhost:11434/health"],
                capture_output=True,
                timeout=2
            )
            if result.returncode == 0:
                print(f"[startup] ✓ Model server ready!")
                break
        except:
            pass
        print(f"  {i+1}/30...", end="\r")
        time.sleep(1)

    # Step 3: Start docker-compose services
    print("\n[startup] Starting CTOAi services (PostgreSQL, Redis, etc)...")
    
    # Load .env to check credentials
    env_file = ROOT / ".env"
    if not env_file.exists():
        print(f"[startup] ✗ .env not found! Create from .env.example:")
        print(f"  cp .env.example .env")
        return 1

    run_cmd(
        ["docker", "compose", "up", "-d", "ctoa-db", "ctoa-redis"],
        "Start database services",
        background=True
    )

    # Wait for services
    print("[startup] Waiting for services (15 seconds)...")
    time.sleep(15)

    # Step 4: Test local model
    print("\n[startup] Testing local model connection...")
    result = subprocess.run(
        [sys.executable, "scripts/test_local_model.py", "--health-only"],
        capture_output=True,
        text=True
    )
    
    if "PASSED" in result.stdout or result.returncode == 0:
        print("[startup] ✓ Model connection successful!")
    else:
        print("[startup] ⚠ Model health check failed, but continuing...")
        print(result.stdout)

    # Step 5: Show status
    print(f"""
╔════════════════════════════════════════════════════════════╗
║                    ✓ STARTUP COMPLETE!                   ║
╠════════════════════════════════════════════════════════════╣
║                                                            ║
║  Model Server:                                             ║
║    Local: http://localhost:11434/v1                       ║
║                                                            ║
║  Database:                                                 ║
║    PostgreSQL: localhost:5432 (ctoa/ctoa)                ║
║    Redis: localhost:6379                                  ║
║                                                            ║
║  VSCode:                                                   ║
║    Open CTOAi folder and use local model!                ║
║                                                            ║
║  Next:                                                     ║
║    1. cd {str(ROOT)}                                      ║
║    2. code .                                              ║
║    3. Chat with local AI!                                ║
║                                                            ║
╚════════════════════════════════════════════════════════════╝
    """)

    # Step 6: Open VSCode (optional)
    try:
        print("[startup] Opening VSCode...")
        # Try different ways to launch VSCode
        vscode_paths = [
            "code",  # If in PATH
            "C:\\Program Files\\Microsoft VS Code\\Code.exe",
            "C:\\Program Files (x86)\\Microsoft VS Code\\Code.exe",
            os.path.expanduser("~\\AppData\\Local\\Programs\\Microsoft VS Code\\Code.exe"),
        ]
        
        launched = False
        for vscode_path in vscode_paths:
            try:
                subprocess.Popen([vscode_path, str(ROOT)])
                launched = True
                break
            except:
                continue
        
        if not launched:
            print(f"[startup] Could not auto-open VSCode")
            print(f"[startup] Manual: Open folder C:\\Users\\zycie\\CTOAi in VSCode")
        else:
            print(f"[startup] ✓ VSCode opened")
    except Exception as e:
        print(f"[startup] Error opening VSCode: {e}")
        print(f"[startup] Manual: Open folder C:\\Users\\zycie\\CTOAi in VSCode")

    print("""
═════════════════════════════════════════════════════════════

Model jest teraz dostępny LOKALNIE na:
  http://localhost:11434/v1

Wszystkie agenty (STRATEGOS + 10 agentów) używają tego modelu.

Aby zatrzymać wszystko:
  docker compose down

Aby zobaczyć logi:
  docker compose logs -f

═════════════════════════════════════════════════════════════
    """)

    return 0


if __name__ == "__main__":
    sys.exit(main())
