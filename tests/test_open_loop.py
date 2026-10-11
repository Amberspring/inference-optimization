import importlib.util
from pathlib import Path

import pytest


PATH = Path(__file__).resolve().parents[1] / "scripts/benchmark_open_loop.py"
SPEC = importlib.util.spec_from_file_location("benchmark_open_loop", PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_summary_counts_errors_and_percentiles():
    rows = [
        {"status": "ok", "ttft_ms": 10, "e2e_ms": 100, "usage": {"completion_tokens": 5}},
        {"status": "ok", "ttft_ms": 20, "e2e_ms": 200, "usage": {"completion_tokens": 5}},
        {"status": "client_overflow"},
    ]
    summary = MODULE.summarize(rows, 3, 1, 2)
    assert summary["completed"] == 2
    assert summary["error_rate"] == pytest.approx(1 / 3)
    assert summary["p95_ttft_ms"] == 20 and summary["output_tokens_per_second"] == 5


def test_workload_accepts_frozen_eval_prompt(tmp_path):
    path = tmp_path / "eval.jsonl"
    path.write_text('{"id":"q1","prompt":"real prompt"}\n', encoding="utf-8")
    assert MODULE.load_workload(path) == [{"id": "q1", "prompt": "real prompt"}]
