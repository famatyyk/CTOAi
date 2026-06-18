# Jak używać lokalnego modelu AI jako Copilota w VSCode

## ✅ Opcja 1: Codeium (darmowy, najszybszy)

**Instalacja:**
1. VSCode → Extensions (Ctrl+Shift+X)
2. Szukaj: `Codeium`
3. Install
4. Zaloguj się (darmowe)

**Jak używać:**
- Pisz kod, Codeium sugeruje automatycznie
- Alt+\ aby zaakceptować sugestię
- Ctrl+Alt+\ aby przejść do następnej sugestii

---

## ✅ Opcja 2: Continue (integracja z twoim lokalnym modelem)

**Instalacja:**
1. VSCode → Extensions (Ctrl+Shift+X)
2. Szukaj: `Continue`
3. Install

**Konfiguracja dla twojego lokalnego modelu:**

1. VSCode → Settings (Ctrl+,)
2. Szukaj: `continue`
3. Kliknij: "Edit in settings.json"

**Dodaj tę konfigurację:**

```json
"continue.serverUrl": "http://localhost:11434/v1"
```

Lub edytuj plik `~/.continue/config.json`:

```json
{
  "models": [
    {
      "title": "Qwen2.5-Coder (Local)",
      "provider": "openai",
      "model": "hf.co/bartowski/Qwen2.5-Coder-1.5B-Instruct-GGUF",
      "apiBase": "http://localhost:11434/v1",
      "apiKey": "local"
    }
  ],
  "tabAutocompleteModel": {
    "title": "Qwen2.5-Coder (Local)",
    "provider": "openai",
    "model": "hf.co/bartowski/Qwen2.5-Coder-1.5B-Instruct-GGUF",
    "apiBase": "http://localhost:11434/v1",
    "apiKey": "local"
  }
}
```

**Restart VSCode** i gotowe! Continue będzie używać twojego lokalnego modelu.

---

## ✅ Opcja 3: GitHub Copilot (płatny, najlepszy)

1. VSCode → Extensions
2. Szukaj: `GitHub Copilot`
3. Install
4. Zaloguj się GitHub
5. Subskrypcja: $10/miesiąc

(Ale oczywiście lokalny model jest FREE!)

---

## ✅ Opcja 4: Cursor (IDE z AI wbudowanym)

Alternatywa do VSCode z Copilota wbudowanym:
- Pobierz: https://cursor.com
- Zbudowany na VSCode
- Integruje się z lokalnym modelem
- Free + Pro opcje

---

## Moja rekomendacja:

### Dla CodeCompletion (szybkie sugestie)
→ **Codeium** (darmowy, szybki, nie potrzebuje konfigu)

### Do rozmowy z AI (czat)
→ **Continue** + twój lokalny model (100% FREE, prywatny)

### Do refaktoringu kodu
→ **Continue** (wbijasz `Ctrl+L`, piszesz co zrobić, model refaktoruje)

---

## Quick Setup (3 minuty)

### Terminal w VSCode:
```bash
# 1. Upewnij się że model server biegnie
docker model run hf.co/bartowski/Qwen2.5-Coder-1.5B-Instruct-GGUF &

# 2. Zainstaluj Continue extension
# (via VSCode UI: Ctrl+Shift+X → Continue → Install)

# 3. Edytuj ~/.continue/config.json (albo create)
# Dodaj konfigurację lokalnego modelu (patrz wyżej)

# 4. Restart VSCode
```

### Gotowe! Teraz:
- **Tab** → Auto-complete (od Continue)
- **Ctrl+L** → Chat z modelem
- **Cmd+K** → Refactor

---

## Test czy działa

**VSCode Terminal (Ctrl+`):**

```bash
# Sprawdź czy model odpowiada
curl http://localhost:11434/v1/models

# Powinno zwrócić listę modeli
```

**W edytorze:**
```python
def hello_world():
    # Zacznij pisać, Continue powinien sugerować!
```

---

## Troubleshooting

**Continue nie widzi modelu?**
1. Sprawdź czy model server biegnie: `docker model ls`
2. Sprawdź port: `curl http://localhost:11434/health`
3. Zrestartuj VSCode

**Sugestie są wolne?**
- Model 1.5B może być wolny na CPU
- Zwiększ timeout w config.json
- Lub spróbuj mniejszy model: `Qwen2.5-Coder-0.5B`

**Chcesz szybciej?**
- Zainstaluj GPU support
- Albo włącz Codeium (cloud-based, fast)

---

## Finalna Setup Instrukcja

```bash
# Terminal
cd C:\Users\zycie\CTOAi

# 1. Uruchom model (jeśli nie biegnie)
docker model run hf.co/bartowski/Qwen2.5-Coder-1.5B-Instruct-GGUF &

# 2. Otwórz VSCode
code .

# 3. Zainstaluj extension (VSCode → Ctrl+Shift+X → Continue)

# 4. Config Continue (jeśli chcesz lokalny model)
# Edytuj: ~/.continue/config.json z konfiguracją wyżej

# 5. Restart VSCode (Ctrl+Shift+P → Reload)

# 6. Test - pisz kod, Continue sugeruje!
```

**Gotowe! Masz Copilota na LOKALNYM modelu - FREE! 🚀**
