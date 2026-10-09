#!/usr/bin/env bash
set -euxo pipefail
export PATH=/root/miniconda3/bin:$PATH
cd /root/autodl-tmp/verification/inference-optimization
test ! -d results/gpu-vllm/20261008-cache-off-output64
for concurrency in 8 16; do
  vllm bench serve --backend vllm --base-url http://127.0.0.1:8000 --model /root/autodl-tmp/hf/hub/models--Qwen--Qwen3-8B/snapshots/b968826d9c46dd6066d109eabc6255188de91218 --served-model-name Qwen3-8B --dataset-name random --random-input-len 128 --random-output-len 64 --random-prefix-len 0 --num-prompts 100 --max-concurrency "$concurrency" --seed 42 --save-result --save-detailed --percentile-metrics ttft,tpot,itl,e2el --metric-percentiles 50,95,99 --result-dir results/gpu-vllm/20261008-cache-off-output64 --result-filename "fp16-input128-output64-c${concurrency}.json"
done
python - <<'PY'
import json
from pathlib import Path
paths = list(Path('results/gpu-vllm/20261008-cache-off-output64').glob('*.json'))
assert len(paths) == 2
records = [json.loads(p.read_text()) for p in paths]
assert all(d['num_prompts'] == d['completed'] == 100 and not any(d['errors']) for d in records)
assert records[0]['input_lens'] == records[1]['input_lens']
print('Two real short-output runs verified; inspect fixed SLO separately')
PY
