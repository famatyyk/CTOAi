# CTOAi Fine-Tune v23 — fix messages format parser
import subprocess, os, json
from pathlib import Path

def run(cmd):
    r = subprocess.run(cmd, shell=True, text=True, capture_output=True)
    print(("OK" if r.returncode==0 else "ERR") + " | " + cmd[:60])
    if r.returncode != 0: print((r.stdout+r.stderr)[-300:])

run("pip install -q trl==0.8.6 peft==0.10.0 transformers==4.40.0 accelerate")

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, TrainingArguments
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

print(f"=== Model ({'fp32 CPU' if not USE_GPU else 'fp16 GPU'}) ===")
if USE_GPU:
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID, torch_dtype=torch.float16, device_map="auto", trust_remote_code=True,
        low_cpu_mem_usage=True
    )
else:
    # CPU: use float32, no device_map
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
    learning_rate=5e-5,  # lower to prevent NaN
    fp16=False,  # CPU: no fp16
    bf16=USE_GPU,  # bf16 on GPU to prevent NaN overflow
    max_grad_norm=1.0,  # gradient clipping
    logging_steps=10,
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
)

trainer.train()
print("=== DONE ===")
trainer.save_model("/kaggle/working/ctoa-lora")
print("Saved to /kaggle/working/ctoa-lora")


