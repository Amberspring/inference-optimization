#!/usr/bin/env bash
set -euo pipefail
export PATH=/root/miniconda3/bin:$PATH
exec vllm serve /root/autodl-tmp/hf/hub/models--Qwen--Qwen3-8B/snapshots/b968826d9c46dd6066d109eabc6255188de91218 --served-model-name Qwen3-8B --host 127.0.0.1 --port 8000 --dtype half --max-model-len 4096 --gpu-memory-utilization 0.85 --max-num-seqs 16 --enable-lora --max-loras 2 --max-lora-rank 16 --lora-modules ecommerce-sft=/root/autodl-tmp/ecommerce-alignment/artifacts/qlora-r16-qv/sft ecommerce-dpo=/root/autodl-tmp/ecommerce-alignment/artifacts/qlora-r16-qv/dpo/policy --no-enable-prefix-caching
