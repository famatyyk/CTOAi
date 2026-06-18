# CTOAi ONE-CLICK START 🚀

## Najszybszy Start

**Opcja 1: Kliknij START.bat (najprościej)**
```
C:\Users\zycie\CTOAi\START.bat
```

Albo skrót na pulpicie: `CTOAi Start.url`

**Co się dzieje automatycznie:**
1. ✓ Sprawdza czy model jest pobrany (jeśli nie → pobiera)
2. ✓ Uruchamia model server na `localhost:11434`
3. ✓ Uruchamia PostgreSQL + Redis
4. ✓ Testuje połączenie
5. ✓ Otwiera VSCode z CTOAi

Gotowe! Model lokalnie dostępny. Zero klikania. 

---

## Opcja 2: Manual (jeśli chcesz kontrolę)

Terminal (cmd.exe lub PowerShell):

```bash
cd C:\Users\zycie\CTOAi

# Terminal 1: Uruchom model
docker model run hf.co/bartowski/Qwen2.5-Coder-1.5B-Instruct-GGUF

# Terminal 2: Uruchom services
docker compose up -d ctoa-db ctoa-redis

# Terminal 3: Otwórz VSCode
code .
```

---

## Opcja 3: Python Script

```bash
cd C:\Users\zycie\CTOAi
python startup.py
```

---

## Weryfikacja że działa

```bash
# Terminal
python scripts/test_local_model.py
```

Powinno wypisać:
```
[test] Provider type: LocalModelProvider
[test] ✓ Provider health check PASSED
[test] Model response received...
```

---

## Co jest gdzie

- **Model server:** http://localhost:11434
- **Database:** localhost:5432 (PostgreSQL)
- **Redis:** localhost:6379
- **VSCode:** Otwiera automatycznie

---

## Jeśli coś nie działa

**Model nie startuje?**
```bash
docker model pull hf.co/bartowski/Qwen2.5-Coder-1.5B-Instruct-GGUF
docker model ls
```

**Port 11434 zajęty?**
```bash
# Zmień w .env
CTOA_LOCAL_MODEL_URL=http://localhost:11435/v1
```

**Baza danych błąd?**
```bash
# Zrestartuj
docker compose down
docker compose up -d ctoa-db ctoa-redis
```

---

## Teraz w VSCode

Masz dostęp do modelu! Możesz używać:

```python
from runner.llm_providers import get_provider

provider = get_provider()
response = provider.complete(
    system_prompt="You are helpful assistant",
    user_prompt="Hello!",
)
print(response)
```

---

**Enjoy! Model jest LOKALNY. Zero kosztów. Pełna kontrola. 🎉**
