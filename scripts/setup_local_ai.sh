#!/bin/bash
# CTOAi Local AI Quick Setup Script

set -e

echo "CTOAi Local AI Model Setup"
echo "============================"
echo ""

# Step 1: Pull Model
echo "[1] Pulling Qwen2.5-Coder model (one-time, ~1GB download)..."
docker model pull hf.co/bartowski/Qwen2.5-Coder-1.5B-Instruct-GGUF

echo "[1] ✓ Model pulled"
docker model ls | grep -i qwen
echo ""

# Step 2: Configure Environment
echo "[2] Setting up local AI environment..."

if [ ! -f .env ]; then
    echo "Creating .env from template..."
    cp .env.example .env 2>/dev/null || echo "# CTOAi Configuration" > .env
fi

# Add local AI config if not already present
if ! grep -q "CTOA_LLM_PROVIDER" .env; then
    cat >> .env <<EOF

# Local AI Model Configuration
CTOA_LLM_PROVIDER=auto
CTOA_LOCAL_MODEL_URL=http://localhost:11434/v1
CTOA_LOCAL_MODEL_NAME=hf.co/bartowski/Qwen2.5-Coder-1.5B-Instruct-GGUF
CTOA_LOCAL_MODEL_TIMEOUT_SECS=120
EOF
    echo "[2] ✓ Environment configured"
else
    echo "[2] ✓ Environment already configured"
fi
echo ""

# Step 3: Install Python Dependencies
echo "[3] Installing dependencies..."
pip install httpx openai -q
echo "[3] ✓ Dependencies installed"
echo ""

# Step 4: Test Integration
echo "[4] Testing local model integration..."
python3 scripts/test_local_model.py --health-only

if [ $? -eq 0 ]; then
    echo ""
    echo "=========================================="
    echo "✓ SUCCESS! Local AI model is ready"
    echo "=========================================="
    echo ""
    echo "Next steps:"
    echo "1. Run a test completion:"
    echo "   python3 scripts/test_local_model.py"
    echo ""
    echo "2. Try STRATEGOS + Agent examples:"
    echo "   python3 scripts/example_strategos_local_ai.py"
    echo ""
    echo "3. Start your agents:"
    echo "   python3 runner/runner.py tick --agents"
    echo ""
    echo "4. Deploy to VPS:"
    echo "   scp .env.local-ai ctoa@46.225.110.52:/opt/ctoa/.env.local-ai"
    echo "   ssh ctoa@46.225.110.52 docker model pull hf.co/bartowski/Qwen2.5-Coder-1.5B-Instruct-GGUF"
    echo ""
else
    echo ""
    echo "=========================================="
    echo "✗ FAILED: Local model health check failed"
    echo "=========================================="
    echo ""
    echo "Troubleshooting:"
    echo "1. Is Docker Model Runner running?"
    echo "   docker model run hf.co/bartowski/Qwen2.5-Coder-1.5B-Instruct-GGUF &"
    echo ""
    echo "2. Check port 11434 is accessible:"
    echo "   curl http://localhost:11434/health"
    echo ""
    echo "3. Check firewall/networking in Docker Desktop settings"
    echo ""
    exit 1
fi
