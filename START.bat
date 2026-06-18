@echo off
cd /d "%~dp0"

echo ============================================================
echo       CTOAi START - Uruchomienie (CPU-only)
echo ============================================================
echo.

echo [1/5] Sprawdzanie Ollama...
"C:\Users\zycie\AppData\Local\Programs\Ollama\ollama.exe" --version
if errorlevel 1 (
    echo [X] Ollama nie jest zainstalowana!
    pause
    exit /b 1
)

echo [1/5] Sprawdzanie modelu...
"C:\Users\zycie\AppData\Local\Programs\Ollama\ollama.exe" list | findstr /i "qwen" >nul
if errorlevel 1 (
    echo [1/5] Model nie znaleziony. Pobieranie...
    "C:\Users\zycie\AppData\Local\Programs\Ollama\ollama.exe" pull qwen2.5-coder:1.5b
) else (
    echo [1/5] OK Model juz pobrany
)

echo.
echo [2/5] Uruchamianie Ollama na localhost:11434 (CPU-only)...
set OLLAMA_NUM_GPU=0
start "CTOAi Ollama Server" "C:\Users\zycie\AppData\Local\Programs\Ollama\ollama.exe" serve
timeout /t 5 /nobreak

echo.
echo [3/5] Otwieranie VSCode...
start "" "C:\Program Files\Microsoft VS Code\Code.exe" "%CD%"

echo.
echo ============================================================
echo              OK GOTOWE (CPU-only mode)
echo ============================================================
echo.
echo  Ollama server uruchomiony w osobnym oknie
echo  Dostepny na:  http://localhost:11434/v1
echo  Tryb: CPU-only (uniknieto bledow CUDA)
echo.
echo ============================================================
echo.
pause