"""CLI dry-run regression: no GPU job is accidentally executed or reported measured."""
import json,subprocess,sys
from pathlib import Path

def test_formal_cli_dry_run(tmp_path):
    root=Path(__file__).resolve().parents[1]
    result=subprocess.run([sys.executable,str(root/'scripts/serve_vllm.py'),'--model','qwen-fixture','--prefix-cache','off'],capture_output=True,text=True,check=True)
    assert '--no-enable-prefix-caching' in result.stdout and 'ecommerce-model' in result.stdout
    result=subprocess.run([sys.executable,str(root/'scripts/benchmark_vllm.py'),'--model','qwen-fixture','--label','fp16'],cwd=tmp_path,capture_output=True,text=True,check=True)
    plan=json.loads((tmp_path/'results/gpu-benchmark-plan.json').read_text(encoding='utf-8'))
    assert plan['status']=='planned_not_run' and len(plan['commands'])==15
    assert all('--save-detailed' in command and '--served-model-name' in command for command in plan['commands'])

