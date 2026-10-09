#!/usr/bin/env bash
set -euo pipefail
export PATH=/root/miniconda3/bin:$PATH
cd /root/autodl-tmp/verification
python -c 'import torch; import torch._inductor.compile_fx; print(torch.__version__)'
nvidia-smi > nvidia-before-20261008.txt
python -m pip freeze > packages-20261008.txt
sha256sum /root/autodl-tmp/ecommerce-alignment/artifacts/qlora-r16-qv/sft/adapter_model.safetensors /root/autodl-tmp/ecommerce-alignment/artifacts/qlora-r16-qv/sft/adapter_config.json /root/autodl-tmp/ecommerce-alignment/artifacts/qlora-r16-qv/dpo/policy/adapter_model.safetensors /root/autodl-tmp/ecommerce-alignment/artifacts/qlora-r16-qv/dpo/policy/adapter_config.json > adapter-sha256-20261008.txt
exec vllm serve /root/autodl-tmp/hf/hub/models--Qwen--Qwen3-8B/snapshots/b968826d9c46dd6066d109eabc6255188de91218 --served-model-name Qwen3-8B --host 127.0.0.1 --port 8000 --dtype half --max-model-len 4096 --gpu-memory-utilization 0.85 --max-num-seqs 16 --enable-lora --max-loras 2 --max-lora-rank 16 --lora-modules ecommerce-sft=/root/autodl-tmp/ecommerce-alignment/artifacts/qlora-r16-qv/sft ecommerce-dpo=/root/autodl-tmp/ecommerce-alignment/artifacts/qlora-r16-qv/dpo/policy
