# 可直接用于简历的正文

**Qwen3-8B 在线推理服务与性能优化｜vLLM、FastAPI、Redis、Prometheus**

将客服模型与金融 RAG 接入统一 FastAPI 网关，实现 OpenAI-compatible 后端、热点缓存、同问并发合并、令牌桶限流、超时、熔断、降级、结构化日志与 Prometheus 指标。基于 vLLM 0.11.0 在 RTX 4080 SUPER 32GB 上部署 Qwen3-8B FP16，配置 4096 上下文、chunked prefill、paged KV cache 与连续批处理；实测模型权重占 15.27GiB、可用 KV cache 10.03GiB/73,024 tokens。固定 128-token 输入、64-token 输出、20 请求时，并发 1→16 的输出吞吐由 40.62 提升至 356.30 tokens/s，总吞吐由 125.33 提升至 1099.31 tokens/s，P95 TTFT 由 44.52ms 增至 124.00ms。共享 256-token 前缀、并发 8 的单轮对照中，开启 prefix cache 后输出吞吐为 207.06 tokens/s（关闭时 183.24），P95 TTFT 为 617.83ms（关闭时 884.29ms）。

边界：以上是单轮、固定随机 token 工作负载，不是生产容量承诺；AWQ/GPTQ/INT8 与真实 Redis 性能尚未实测，因此不在简历中声称量化收益或 Redis 加速比例。
