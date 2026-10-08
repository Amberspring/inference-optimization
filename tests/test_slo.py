import importlib.util
import json
from pathlib import Path
import pytest


def test_slo_rejects_failure_and_missing_measurement(tmp_path):
    spec = importlib.util.spec_from_file_location("slo", Path(__file__).resolve().parents[1] / "scripts/analyze_slo.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    fixture = {"num_prompts": 100, "completed": 100, "p95_ttft_ms": 50, "p95_e2el_ms": 500,
               "request_throughput": 2, "max_concurrency": 4, "model_id": "fixture", "duration": 50,
               "total_input_tokens": 1000, "total_output_tokens": 2000}
    path = tmp_path / "run.json"
    path.write_text(json.dumps(fixture))
    assert module.analyze([path], 100, 1000, .01)["best_observed"]["concurrency"] == 4
    path.write_text(json.dumps({**fixture, "completed": 80}))
    assert module.analyze([path], 100, 1000, .01)["best_observed"] is None
    path.write_text(json.dumps({**fixture, "p95_ttft_ms": None}))
    with pytest.raises(ValueError):
        module.analyze([path], 100, 1000, .01)
