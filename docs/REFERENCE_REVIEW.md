# Reference review

Reviewed yyy32575/ecommerce-post-training, graphrag-travel-qa and vllm-inference-optimization on 2026-10-05.
Useful ideas retained: evaluation dimensions, badcase buckets, SLO-constrained comparison, workload length distributions and recovery runbooks. Implementations here reuse our existing code and official TRL/PEFT/vLLM tools; no source copied from these repositories. No LICENSE file was listed in their repository trees.
The public GraphRAG README calls its figures estimates. The GRPO implementation converts the model loss to a float and recreates a disconnected tensor before backward. Its vLLM runner counts network chunks as tokens. These are not accepted as experiment evidence or reused measurement methods.

Sources:
- https://github.com/yyy32575/ecommerce-post-training
- https://github.com/yyy32575/graphrag-travel-qa
- https://github.com/yyy32575/vllm-inference-optimization
