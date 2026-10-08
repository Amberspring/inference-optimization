import json
import runpy
import sys
from pathlib import Path


def test_planning_never_claims_execution_and_records_cache_protocol(tmp_path, monkeypatch):
    path = Path(__file__).resolve().parents[1] / "scripts/benchmark_vllm.py"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", [str(path), "--model", "fixture", "--label", "fp16", "--reset-prefix-cache", "--run-id", "fixture"])
    runpy.run_path(str(path), run_name="__main__")
    report = json.loads((tmp_path / "results/gpu-benchmark-plan.json").read_text())
    assert report["status"] == "planned_not_run" and report["reset_prefix_cache_before_each_run"]
    assert len(report["commands"]) == 15
