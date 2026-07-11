# CTOAi Fine-Tune v26 — stability + OOM-safe load
import json
import math
import os
import random
import re

# Controlled Kaggle dependency bootstrap only.
import subprocess  # nosec B404
import sys


def run(cmd):
    # cmd is a fixed argv list from this notebook, not user-provided shell text.
    r = subprocess.run(cmd, text=True, capture_output=True)  # nosec B603
    display = " ".join(cmd)
    print(("OK" if r.returncode == 0 else "ERR") + " | " + display[:60])
    if r.returncode != 0:
        print((r.stdout + r.stderr)[-300:])


PINNED_REVISION_RE = re.compile(r"^[0-9a-f]{40}$")


def require_pinned_model_revision() -> str:
    revision = os.environ.get("CTOA_TRAINING_MODEL_REVISION", "").strip().lower()
    if not PINNED_REVISION_RE.fullmatch(revision):
        raise RuntimeError(
            "CTOA_TRAINING_MODEL_REVISION must be set to an immutable "
            "40-character Hugging Face git commit SHA before model download."
        )
    return revision


def trust_remote_code_enabled() -> bool:
    return os.environ.get("CTOA_TRAINING_TRUST_REMOTE_CODE", "").strip().lower() in {
        "1",
        "true",
        "yes",
    }


run(
    [
        sys.executable,
        "-m",
        "pip",
        "install",
        "-q",
        "trl==0.8.6",
        "peft==0.10.0",
        "transformers==4.40.0",
        "accelerate",
        "bitsandbytes",
    ]
)

import torch  # noqa: E402
from datasets import Dataset  # noqa: E402
from peft import LoraConfig, TaskType, get_peft_model  # noqa: E402
from transformers import (  # noqa: E402
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    TrainerCallback,
    TrainingArguments,
)
from trl import SFTTrainer  # noqa: E402

# GPU check - force CPU if P100
if torch.cuda.is_available():
    cap = torch.cuda.get_device_capability(0)
    gpu_name = torch.cuda.get_device_name(0)
    print(f"GPU: {gpu_name} | sm_{cap[0]}{cap[1]}")
    USE_GPU = cap[0] >= 7
    if not USE_GPU:
        print("P100 sm_60 detected - USING CPU")
else:
    USE_GPU = False
    print("No CUDA - CPU only")

DEVICE = "cuda" if USE_GPU else "cpu"
print(f"Training device: {DEVICE}")

# Auto-detect dataset
DATASET_PATH = None
for root, dirs, files in os.walk("/kaggle/input"):
    for f in files:
        if f.endswith(".jsonl"):
            DATASET_PATH = os.path.join(root, f)
            break
    if DATASET_PATH:
        break
print("Dataset:", DATASET_PATH)
if DATASET_PATH is None:
    raise RuntimeError("No .jsonl dataset found under /kaggle/input.")

MODEL_ID = "Qwen/Qwen2.5-Coder-1.5B-Instruct"
MODEL_REVISION = require_pinned_model_revision()
TRUST_REMOTE_CODE = trust_remote_code_enabled()

print("=== Tokenizer ===")
tokenizer = AutoTokenizer.from_pretrained(
    MODEL_ID,
    revision=MODEL_REVISION,
    trust_remote_code=TRUST_REMOTE_CODE,
)
tokenizer.pad_token = tokenizer.eos_token
print("OK")

print(f"=== Model ({'fp32 CPU' if not USE_GPU else 'fp32 GPU'}) ===")
if USE_GPU:
    # Memory-safe load on T4: 4-bit NF4 weights, bf16 compute.
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True,
        bnb_4bit_compute_dtype=torch.bfloat16,
    )
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID,
        revision=MODEL_REVISION,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=TRUST_REMOTE_CODE,
        low_cpu_mem_usage=True,
    )
else:
    # CPU: use float32, no quantization
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID,
        revision=MODEL_REVISION,
        torch_dtype=torch.float32,
        device_map=None,
        trust_remote_code=TRUST_REMOTE_CODE,
        low_cpu_mem_usage=True,
    )
    model = model.to("cpu")
print("Model OK")

print("=== LoRA ===")
lora = LoraConfig(
    r=4,
    lora_alpha=8,
    target_modules=["q_proj", "v_proj"],  # fewer modules for speed
    lora_dropout=0.05,
    bias="none",
    task_type=TaskType.CAUSAL_LM,
    inference_mode=False,
)
model = get_peft_model(model, lora)
model.print_trainable_parameters()
# Disable cache for training stability/perf and memory behavior.
model.config.use_cache = False


class FiniteGuardCallback(TrainerCallback):
    """Stop immediately when loss or LoRA params become non-finite."""

    def on_log(self, args, state, control, logs=None, model=None, **kwargs):
        if logs and "loss" in logs:
            loss = float(logs["loss"])
            if not math.isfinite(loss):
                raise RuntimeError(f"Non-finite loss detected: {loss}")

    def on_step_end(self, args, state, control, model=None, **kwargs):
        if model is None:
            return
        for name, param in model.named_parameters():
            if not param.requires_grad:
                continue
            if not torch.isfinite(param).all():
                raise RuntimeError(f"Non-finite trainable parameter detected: {name}")


# Use bf16 training instead of fp16 to prevent NaN

print("=== Dataset ===")
rows = []
with open(DATASET_PATH) as fh:
    for line in fh:
        line = line.strip()
        if not line:
            continue
        obj = json.loads(line)
        # Support both formats: messages (role/content) and conversations (from/value)
        msgs = obj.get("messages") or obj.get("conversations") or []
        text = ""
        for m in msgs:
            role = m.get("role") or m.get("from") or ""
            content = m.get("content") or m.get("value") or ""
            if role == "system":
                text += f"<|im_start|>system\n{content}<|im_end|>\n"
            elif role in ("user", "human"):
                text += f"<|im_start|>user\n{content}<|im_end|>\n"
            elif role in ("assistant", "gpt"):
                text += f"<|im_start|>assistant\n{content}<|im_end|>\n"
        if text.strip():
            rows.append({"text": text})

# Use only 200 examples for CPU training (time limit ~9h on Kaggle)
random.seed(42)
random.shuffle(rows)
rows = rows[:200]
print(f"{len(rows)} examples (CPU subset)")

dataset = Dataset.from_list(rows)

print("=== Train ===")
args = TrainingArguments(
    output_dir="/kaggle/working/ctoa-lora",
    num_train_epochs=1,
    per_device_train_batch_size=1,
    gradient_accumulation_steps=4,
    learning_rate=1e-5,  # extra conservative to avoid divergence
    warmup_ratio=0.1,
    lr_scheduler_type="cosine",
    weight_decay=0.01,
    optim="adamw_torch",
    fp16=False,  # CPU: no fp16
    bf16=USE_GPU,  # use bf16 only inside Trainer autocast on GPU
    max_grad_norm=0.3,  # tighter gradient clipping
    logging_steps=10,
    logging_first_step=True,
    save_strategy="epoch",
    no_cuda=not USE_GPU,
    dataloader_pin_memory=False,
    report_to="none",
    max_steps=100,  # limit for CPU: ~30min
)

trainer = SFTTrainer(
    model=model,
    args=args,
    train_dataset=dataset,
    tokenizer=tokenizer,
    dataset_text_field="text",
    max_seq_length=512,
    callbacks=[FiniteGuardCallback()],
)

trainer.train()
print("=== DONE ===")
trainer.save_model("/kaggle/working/ctoa-lora")
print("Saved to /kaggle/working/ctoa-lora")
