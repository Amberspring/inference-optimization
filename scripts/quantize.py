"""Real PTQ entrypoint; requires Linux/CUDA/llm-compressor. Not run in the CPU deliverable."""

import argparse, json, hashlib
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument("--model", required=True)
p.add_argument("--data", required=True)
p.add_argument("--scheme", choices=["awq", "gptq", "int8"], required=True)
p.add_argument("--output", required=True)
p.add_argument("--samples", type=int, default=128)
a = p.parse_args()
import torch

if not torch.cuda.is_available():
    raise RuntimeError("CUDA required for this quantization profile")
from transformers import AutoModelForCausalLM, AutoTokenizer
from datasets import Dataset
from llmcompressor import oneshot
from llmcompressor.modifiers.gptq import GPTQModifier
from llmcompressor.modifiers.quantization import QuantizationModifier
from llmcompressor.modifiers.transform.awq import AWQModifier
from llmcompressor.modifiers.transform.smoothquant import SmoothQuantModifier

tok = AutoTokenizer.from_pretrained(a.model)
raw = [
    json.loads(s)
    for s in Path(a.data).read_text(encoding="utf-8").splitlines()
    if s.strip()
]
if len(raw) < a.samples:
    raise ValueError(
        "Too few independent calibration examples; do not duplicate fixtures to pretend to have a large corpus"
    )
ds = Dataset.from_list(
    [
        {
            "text": tok.apply_chat_template(
                [
                    {"role": "user", "content": r["prompt"]},
                    {"role": "assistant", "content": r["completion"]},
                ],
                tokenize=False,
                enable_thinking=False,
            )
        }
        for r in raw[: a.samples]
    ]
)
model = AutoModelForCausalLM.from_pretrained(a.model, torch_dtype=torch.float16)
if a.scheme == "awq":
    recipe = [
        AWQModifier(duo_scaling="both"),
        QuantizationModifier(
            ignore=["lm_head"], scheme="W4A16_ASYM", targets=["Linear"]
        ),
    ]
elif a.scheme == "gptq":
    recipe = [GPTQModifier(targets="Linear", scheme="W4A16", ignore=["lm_head"])]
else:
    recipe = [
        SmoothQuantModifier(smoothing_strength=0.8),
        GPTQModifier(targets="Linear", scheme="W8A8", ignore=["lm_head"]),
    ]
oneshot(
    model=model,
    dataset=ds,
    recipe=recipe,
    max_seq_length=1024,
    num_calibration_samples=a.samples,
)
model.save_pretrained(a.output, save_compressed=True)
tok.save_pretrained(a.output)
Path(a.output, "quantization-run.json").write_text(
    json.dumps(
        {
            "status": "measured",
            "scheme": a.scheme,
            "source_model": a.model,
            "calibration_sha256": hashlib.sha256(Path(a.data).read_bytes()).hexdigest(),
            "calibration_samples": a.samples,
            "gpu": torch.cuda.get_device_name(),
            "peak_allocated_bytes": torch.cuda.max_memory_allocated(),
        },
        indent=2,
    ),
    encoding="utf-8",
)
