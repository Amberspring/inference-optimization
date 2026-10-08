"""Start both installed packages locally; shut down only subprocesses owned by this launcher."""

import os, sys, subprocess, time, argparse
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument(
    "--tiny",
    action="store_true",
    help="Use project-one trained tiny CPU policy, not the mock backend",
)
args = parser.parse_args()
env = {**os.environ, "BACKEND": os.getenv("BACKEND", "mock")}
services = [("finrag.api:app", 8001), ("gateway.service:app", 8002)]
if args.tiny:
    checkpoint = (
        Path(__file__).resolve().parents[1].parent
        / "ecommerce-alignment/artifacts/trl-smoke/merged"
    )
    if not checkpoint.exists():
        raise RuntimeError(
            "Train project-one tiny policy first: python -m ecom.trl_smoke"
        )
    env.update(
        BACKEND="openai",
        MODEL_URL="http://127.0.0.1:8000/v1",
        MODEL="tiny-qwen3",
        MODEL_PATH=str(checkpoint),
        TIMEOUT="30",
        MODEL_CORPUS_VERSION="tiny-trained-cpu-v1",
    )
    services.insert(0, ("ecom.cpu_api:app", 8000))

children = []
try:
    for module, port in services:
        children.append(
            subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    module,
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(port),
                ],
                env=env,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
        )
    print(
        "RAG demo: http://127.0.0.1:8001 ; Gateway API: http://127.0.0.1:8002/docs ; Ctrl+C stops both.",
        flush=True,
    )
    while all(p.poll() is None for p in children):
        time.sleep(0.5)
    raise RuntimeError("One service stopped; inspect the service output above.")
except KeyboardInterrupt:
    pass
finally:
    for child in children:
        if child.poll() is None:
            child.terminate()
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()
