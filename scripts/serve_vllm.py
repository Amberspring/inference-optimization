import argparse, subprocess, sys

p = argparse.ArgumentParser()
p.add_argument("--model", required=True)
p.add_argument(
    "--quantization",
    choices=["auto", "awq", "gptq", "compressed-tensors"],
    default="auto",
)
p.add_argument("--max-model-len", type=int, default=4096)
p.add_argument("--port", type=int, default=8000)
p.add_argument("--execute", action="store_true")
p.add_argument("--prefix-cache", choices=["on", "off"], default="on")
p.add_argument("--max-num-batched-tokens", type=int, default=4096)
p.add_argument("--served-model-name", default="ecommerce-model")
p.add_argument("--dtype", choices=["auto", "half", "bfloat16"], default="half")
a = p.parse_args()
cmd = [
    "vllm",
    "serve",
    a.model,
    "--served-model-name",
    a.served_model_name,
    "--dtype",
    a.dtype,
    "--host",
    "127.0.0.1",
    "--port",
    str(a.port),
    "--max-model-len",
    str(a.max_model_len),
    "--gpu-memory-utilization",
    "0.85",
    "--max-num-batched-tokens",
    str(a.max_num_batched_tokens),
    "--enable-prefix-caching"
    if a.prefix_cache == "on"
    else "--no-enable-prefix-caching",
]
if a.quantization != "auto":
    cmd += ["--quantization", a.quantization]
print(" ".join(cmd))
if a.execute:
    if sys.platform == "win32":
        raise RuntimeError("Use Linux NVIDIA GPU environment for this vLLM profile")
    subprocess.run(cmd, check=True)
