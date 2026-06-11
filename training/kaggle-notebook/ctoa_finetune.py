# CTOAi Fine-Tune v26 — stability + OOM-safe load
import subprocess, os, json, math
from pathlib import Path

def run(cmd):
    r = subprocess.run(cmd, shell=True, text=True, capture_output=True)
    print(("OK" if r.returncode==0 else "ERR") + " | " + cmd[:60])
    if r.returncode != 0: print((r.stdout+r.stderr)[-300:])

run("pip install -q trl==0.8.6 peft==0.10.0 transformers==4.40.0 accelerate bitsandbytes")

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, TrainingArguments, TrainerCallback, BitsAndBytesConfig
from peft import LoraConfig, get_peft_model, TaskType
from trl import SFTTrainer
from datasets import Dataset

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
    if DATASET_PATH: break
print("Dataset:", DATASET_PATH)
assert DATASET_PATH

MODEL_ID = "Qwen/Qwen2.5-Coder-1.5B-Instruct"

print("=== Tokenizer ===")
tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, trust_remote_code=True)
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
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True,
        low_cpu_mem_usage=True,
    )
else:
    # CPU: use float32, no quantization
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID, torch_dtype=torch.float32, device_map=None, trust_remote_code=True,
        low_cpu_mem_usage=True
    )
    model = model.to("cpu")
print("Model OK")

print("=== LoRA ===")
lora = LoraConfig(
    r=4, lora_alpha=8,
    target_modules=["q_proj","v_proj"],  # fewer modules for speed
    lora_dropout=0.05, bias="none",
    task_type=TaskType.CAUSAL_LM,
    inference_mode=False
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
        if not line: continue
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
import random
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





