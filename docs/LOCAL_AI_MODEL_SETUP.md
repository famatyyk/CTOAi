# Local AI Model Integration for CTOAi

This guide sets up **local AI models** (Qwen2.5-Coder via Docker Model Runner) for your CTOAi agents, eliminating API costs and keeping data private.

## Quick Start

### 1. Pull the Model (One-Time)

```bash
docker model pull hf.co/bartowski/Qwen2.5-Coder-1.5B-Instruct-GGUF
```

This downloads ~1GB and caches it locally. Verify:
```bash
docker model ls
```

### 2. Load Environment

```bash
# Option A: Copy example config
cp .env.local-ai .env

# Option B: Add to existing .env
echo 'CTOA_LLM_PROVIDER=auto' >> .env
echo 'CTOA_LOCAL_MODEL_URL=http://localhost:11434/v1' >> .env
```

### 3. Test Locally

```bash
# From repo root
python3 scripts/test_local_model.py --health-only

# If health passes, test a completion
python3 scripts/test_local_model.py --invoke "Write a Python function to sum two numbers"
```

### 4. Deploy to VPS

```bash
# On your VPS (46.225.110.52):
ssh ctoa@46.225.110.52

# Pull model once
docker model pull hf.co/bartowski/Qwen2.5-Coder-1.5B-Instruct-GGUF

# Update .env on VPS
echo 'CTOA_LLM_PROVIDER=auto' >> /opt/ctoa/.env

# Restart runners (agents will auto-use local model)
cd /opt/ctoa
python3 runner/runner.py tick --agents
```

## Architecture

### Provider Factory

The system auto-detects available LLM provider:

```
┌─────────────────────────────────┐
│  get_provider()                 │
│  (llm_providers/__init__.py)     │
└────────────────────┬────────────┘
                     │
         ┌───────────┴────────────┐
         │                        │
    ┌────▼──────┐          ┌──────▼──────┐
    │ AZURE_MODE│          │ LOCAL_MODE  │
    └────┬──────┘          └──────┬──────┘
    Azure OpenAI         Docker Model Runner
    (gpt-4o via           (Qwen2.5-Coder via
     Foundry)             llm/v1 API)
```

### Agent Execution Flow

```
runner.py tick --agents
    ↓
execute_agent_for_task(task)
    ↓
invoke_llm_for_task(task_id, prompt)
    ↓
get_provider()  ← Choose: Local or Azure
    ↓
provider.complete(system_prompt, user_prompt)
    ↓
[Qwen2.5-Coder 1.5B response]
    ↓
Write deliverable → task state updates
```

## Configuration Options

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CTOA_LLM_PROVIDER` | `auto` | `local`, `azure`, or `auto` (try local, fallback to azure) |
| `CTOA_LOCAL_MODEL_URL` | `http://localhost:11434/v1` | Docker Model Runner endpoint (OpenAI-compatible) |
| `CTOA_LOCAL_MODEL_NAME` | `hf.co/bartowski/Qwen2.5-Coder-1.5B-Instruct-GGUF` | Model identifier |
| `CTOA_LOCAL_MODEL_TIMEOUT_SECS` | `120` | Request timeout (for slow machines) |
| `FOUNDRY_ENDPOINT` | `` | Azure Foundry endpoint (fallback) |
| `FOUNDRY_API_KEY` | `` | Azure API key (fallback) |

### Usage Patterns

**Force Local Model (fail if unavailable):**
```bash
export CTOA_LLM_PROVIDER=local
python3 scripts/test_local_model.py
```

**Auto-Detect (recommended):**
```bash
export CTOA_LLM_PROVIDER=auto
# Uses local if healthy, falls back to Azure if not
```

**Use Azure Only (ignore local model):**
```bash
export CTOA_LLM_PROVIDER=azure
```

## Model Details

### Qwen2.5-Coder 1.5B (GGUF Quantized)

- **Size:** 986 MB (Q4_K_M quantization)
- **Context:** 8,192 tokens
- **Specialization:** Code generation, documentation, technical writing
- **Performance:** ~500-1000 tokens/sec on CPU (faster on GPU)
- **Cost:** $0 (runs locally)

**Suitable for:**
- Code synthesis
- Runbook generation
- Documentation
- SQL/shell commands
- Architecture decisions

**Not suitable for:**
- Complex reasoning (reasoning models like o1 better)
- Long-context tasks >8K tokens
- Multilingual tasks

## Running with Docker Compose

### Option 1: Manual Model Server

If Docker Model Runner daemon is running:

```bash
# Terminal 1: Ensure model server is running
docker model run hf.co/bartowski/Qwen2.5-Coder-1.5B-Instruct-GGUF

# Terminal 2: Run CTOAi
docker compose up ctoa-db ctoa-redis ctoa
```

### Option 2: Include Model in Compose

Add to `docker-compose.yml`:

```yaml
services:
  ctoa-local-model-api:
    image: alpine:latest
    container_name: ctoa-local-model-api
    ports:
      - "127.0.0.1:11434:11434"
    environment:
      CTOA_LOCAL_MODEL_URL: http://localhost:11434/v1
    profiles:
      - ai
```

Run:
```bash
docker compose --profile ai up -d ctoa-local-model-api
```

## Testing & Debugging

### Health Check

```bash
python3 scripts/test_local_model.py --health-only
```

Expected output:
```
[test] Provider type: LocalModelProvider
[test] ✓ Provider health check PASSED
```

### Test Completion

```bash
python3 scripts/test_local_model.py --invoke "Generate a Python decorator for timing function execution"
```

### Inspect Logs

```bash
# Runner logs
tail -50 logs/runner.log | grep -i llm

# Agent execution
tail -20 logs/runner.log | grep "agent"
```

### Check Model Server

```bash
# Verify model is cached
docker model ls

# Test OpenAI-compatible API directly
curl -X POST http://localhost:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "hf.co/bartowski/Qwen2.5-Coder-1.5B-Instruct-GGUF",
    "messages": [{"role": "user", "content": "Hello"}],
    "temperature": 0.1,
    "max_tokens": 100
  }' | jq .
```

## Troubleshooting

### Model Not Found

```
Error: UNKNOWN - resolving docker.io/.../qwen2.5-coder: pull access denied
```

**Solution:**
```bash
# Pull from HuggingFace instead
docker model pull hf.co/bartowski/Qwen2.5-Coder-1.5B-Instruct-GGUF

# Verify
docker model ls | grep qwen
```

### Health Check Fails

```
[test] ✗ Provider health check FAILED
```

**Causes & Fixes:**

1. **Docker Model Runner not running:**
   ```bash
   # Check if model server is active
   docker model run hf.co/bartowski/Qwen2.5-Coder-1.5B-Instruct-GGUF &
   ```

2. **Wrong endpoint:**
   ```bash
   # Verify endpoint is accessible
   curl -I http://localhost:11434/health
   # Should return 200 OK
   ```

3. **Firewall/networking:**
   ```bash
   # On Docker Desktop or VPS, check port 11434 is exposed
   netstat -tulpn | grep 11434
   ```

### Slow Completions

Local models run on CPU by default. If too slow:

1. **Increase timeout:**
   ```bash
   export CTOA_LOCAL_MODEL_TIMEOUT_SECS=300
   ```

2. **Try smaller model:**
   ```bash
   docker model pull hf.co/bartowski/Qwen2.5-Coder-0.5B-Instruct-GGUF
   ```

3. **Use GPU (if available):**
   ```bash
   # Docker Desktop: Enable GPU in settings
   # VPS: Install NVIDIA container toolkit + set CUDA_VISIBLE_DEVICES
   ```

### Memory Issues

If process crashes with OOM:

1. **Check available memory:**
   ```bash
   free -h
   ```

2. **Reduce context size in .env:**
   ```bash
   # Edit docker-compose.yml or agent config
   context_size: 4096  # Instead of 8192
   ```

3. **Use quantized version:**
   ```bash
   # GGUF Q4 (current) uses ~1GB
   # GGUF Q3_K_M uses ~800MB (slower)
   docker model pull hf.co/bartowski/Qwen2.5-Coder-1.5B-Instruct-GGUF
   ```

## Production Deployment

### VPS Setup Checklist

- [ ] SSH access to VPS configured
- [ ] Docker installed on VPS
- [ ] Docker Model Runner available
- [ ] Model pulled: `docker model pull hf.co/bartowski/...`
- [ ] `.env.local-ai` copied to VPS: `scp .env.local-ai ctoa@VPS:/opt/ctoa/`
- [ ] Environment loaded: `source .env.local-ai`
- [ ] Health check passes: `python3 scripts/test_local_model.py`
- [ ] Systemd timer configured to use local model
- [ ] First agent execution successful: `python3 runner/runner.py tick --agents`

### Systemd Service Update

If using systemd on VPS:

```ini
[Service]
Environment="CTOA_LLM_PROVIDER=auto"
Environment="CTOA_LOCAL_MODEL_URL=http://localhost:11434/v1"
ExecStart=/usr/bin/python3 /opt/ctoa/runner/runner.py tick --agents
```

Then:
```bash
sudo systemctl daemon-reload
sudo systemctl restart ctoa-runner.timer
```

## Cost Comparison

| Method | Setup Cost | Per-Task Cost | Monthly (100 tasks) |
|--------|-----------|-------------|-------------------|
| **Local Model** | 0 USD | 0 USD | 0 USD |
| **Azure GPT-4o** | 0 USD | ~0.15 USD | ~15 USD |
| **Azure GPT-4 Turbo** | 0 USD | ~0.03 USD | ~3 USD |

**Local model advantage:** No API costs, no rate limiting, no data leaving your infrastructure.

## Next Steps

1. **Test locally:** Run `python3 scripts/test_local_model.py`
2. **Modify agents:** Update `runner/agents/executor.py` to use `invoke_llm_for_task()` instead of placeholder logic
3. **Deploy to VPS:** Copy `.env.local-ai` and pull model on VPS
4. **Monitor:** Check agent outputs in `logs/runner.log` for LLM quality
5. **Optimize:** Adjust prompts in `invoke_llm_for_task()` for better deliverables

## References

- [Docker Model Runner](https://docs.docker.com/ai/model-runner/)
- [Qwen2.5-Coder on HuggingFace](https://huggingface.co/Qwen/Qwen2.5-Coder)
- [OpenAI API Compatibility](https://docs.docker.com/ai/model-runner/api-reference/)

Sources:
- https://docs.docker.com/ai/model-runner/
- https://huggingface.co/Qwen/Qwen2.5-Coder
