"""Start owned services, verify real upstream integration, save responses, then stop them."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import httpx


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--model-url", required=True)
    p.add_argument("--model", required=True)
    p.add_argument("--finance-model", required=True)
    p.add_argument("--customer-query", required=True)
    p.add_argument("--finance-query", required=True)
    p.add_argument("--output", required=True)
    a = p.parse_args()
    output = Path(a.output)
    output.mkdir(parents=True, exist_ok=False)
    env = {**os.environ, "BACKEND": "vllm", "MODEL_URL": a.model_url, "MODEL": a.model,
           "FINANCE_MODEL": a.finance_model, "RAG_URL": "http://127.0.0.1:18001",
           "RAG_MODEL_URL": a.model_url, "RAG_MODEL": a.finance_model, "EMBEDDING": "tfidf", "RERANKER": "",
           "TIMEOUT": "60", "MODEL_CORPUS_VERSION": "verification-20261008"}
    children, logs = [], []
    report = {"status": "running", "scope": "Selected integration examples, not answer quality benchmark",
              "model": a.model, "finance_model": a.finance_model, "cases": []}
    try:
        for module, port in [("finrag.api:app", 18001), ("gateway.service:app", 18002)]:
            log = (output / (str(port) + ".log")).open("w", encoding="utf-8")
            logs.append(log)
            children.append(subprocess.Popen([sys.executable, "-m", "uvicorn", module, "--host", "127.0.0.1", "--port", str(port)], env=env,
                                             stdout=log, stderr=subprocess.STDOUT,
                                             creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0))
        with httpx.Client(timeout=60, trust_env=False) as client:
            deadline = time.monotonic() + 45
            while time.monotonic() < deadline:
                if any(child.poll() is not None for child in children):
                    raise RuntimeError("An owned service stopped; inspect saved logs")
                try:
                    ready = [client.get(f"http://127.0.0.1:{port}/health").json() for port in (18001, 18002)]
                    if ready[0]["ready"]:
                        break
                except httpx.HTTPError:
                    pass
                time.sleep(.5)
            else:
                raise TimeoutError("Services did not become ready")
            for body in [{"query": a.customer_query, "task": "customer"},
                         {"query": a.finance_query, "task": "finance", "calculate": True}]:
                response = client.post("http://127.0.0.1:18002/ask", json=body)
                response.raise_for_status()
                data = response.json()
                report["cases"].append({"request": body, "response": data})
                (output / "chain.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
                if data["refused"] or data["degraded"]:
                    raise RuntimeError("Example refused or degraded; integration not accepted")
                if body["task"] == "customer" and not data.get("usage"):
                    raise RuntimeError("Missing real model usage")
                if body["task"] == "finance" and (data["backend"] != "evidence_calculator" or not data["citations"]):
                    raise RuntimeError("Missing controlled financial calculation and citations")
                cached = client.post("http://127.0.0.1:18002/ask", json=body).json()
                if not cached["cached"]:
                    raise RuntimeError("Cache integration failed")
                report["cases"][-1]["repeated_response"] = cached
            metrics = client.get("http://127.0.0.1:18002/metrics")
            metrics.raise_for_status()
            (output / "metrics.txt").write_text(metrics.text, encoding="utf-8")
            report.update(status="verified_real_model_rag_gateway_cache", health=ready)
    except Exception as error:
        report.update(status="failed", error=str(error))
        raise
    finally:
        (output / "chain.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        for child in children:
            if child.poll() is None:
                child.terminate()
                try:
                    child.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait()
        for log in logs:
            log.close()
    print(report["status"])


if __name__ == "__main__":
    main()
