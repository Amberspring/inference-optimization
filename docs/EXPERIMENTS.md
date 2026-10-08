# 本机 HTTP 压测与演练

额外串联了项目一实际 SFT/DPO 后导出的微型 Qwen3 模型，OpenAI-compatible CPU API 给出真实 completion_tokens，网关客服路由返回模型生成，金融路由在引用不合格时退回真实摘录。记录见 results/tiny-model-integration.json；其 scope 明确不是 8B 业务质量或性能实验。下面压测仍使用 mock 后端，不能混用这两种结果。

真实 loopback HTTP，Windows CPU，mock 上游等待 20ms，有界内存 TTL 缓存。每组 100 次，服务并发槽=8，限流 rate/burst=10000。

|并发|负载|成功 QPS|P50 ms|P95 ms|P99 ms|缓存命中数|错误/降级率|
|---:|---|---:|---:|---:|---:|---:|---:|
|1|unique|30.73|31.21|45.54|46.26|0|0.000|
|1|hot|117.62|8.16|9.32|10.51|99|0.000|
|4|unique|101.07|33.84|56.73|64.37|0|0.000|
|4|hot|114.01|29.98|61.92|75.08|99|0.000|
|8|unique|82.59|79.47|155.22|173.88|0|0.000|
|8|hot|85.95|74.69|117.83|134.60|99|0.000|
|16|unique|55.77|192.71|544.49|1019.41|0|0.000|
|16|hot|60.41|187.34|596.42|989.37|99|0.000|
|32|unique|49.65|439.16|1298.29|1593.17|0|0.000|
|32|hot|64.47|334.91|1076.90|1417.51|99|0.000|

每轮原始请求行见 results/benchmark-c*.json；概要见 benchmark-summary.json。output_tokens_per_second 保持 null，因为 mock 没有真实 tokenizer 与模型 usage。

此为单次闭环测试，未提供重复实验区间；高并发受到 Windows、本机客户端与日志开销影响。不能从这些数字推导 vLLM tokens/s、显存、量化加速或生产容量。缓存效果也不能外推到真实 8B 模型。

HTTP 串联结果见 results/http-integration.json；OOM/超时/断开为程序注入演练，原始记录见 fault-drill.json。真实 Redis、AWQ/GPTQ/INT8 尚未运行。

# Qwen3-8B vLLM GPU 实验（2026-10-06）

环境：AutoDL NVIDIA GeForce RTX 4080 SUPER 32GB，vLLM 0.11.0，PyTorch 2.8.0，FP16，`max_model_len=4096`，`gpu_memory_utilization=0.85`，`max_num_batched_tokens=4096`，eager mode。启动日志记录模型权重 15.2683GiB、可用 KV cache 10.03GiB、73,024 KV tokens，4096-token 请求理论最大并发 17.83x。

| 并发 | 请求吞吐 req/s | 输出吞吐 tok/s | 总吞吐 tok/s | P95 TTFT ms | P95 E2E ms |
|---:|---:|---:|---:|---:|---:|
| 1 | 0.67 | 40.62 | 125.33 | 44.52 | 1579.28 |
| 4 | 2.43 | 148.02 | 456.69 | 80.20 | 1664.91 |
| 8 | 3.96 | 241.22 | 744.26 | 87.81 | 1706.05 |
| 16 | 5.85 | 356.30 | 1099.31 | 124.00 | 1787.40 |

工作负载固定为随机 128-token 输入、目标 64-token 输出、20 请求，所有请求成功。prefix cache 对照固定随机 512-token 输入、256-token 共享前缀、64-token 输出、30 请求、并发 8：开启/关闭时输出吞吐分别为 207.06/183.24 tok/s，P95 TTFT 为 617.83/884.29ms，P95 E2E 为 2365.74/2725.96ms。两组均为单轮小样本，结果只支持当前硬件和配置下的工程比较。

原始数据：`results/gpu-vllm/quick/*.json`、`results/gpu-vllm/prefix/*.json`；服务证据：`results/vllm-startup*.txt`、`results/nvidia-smi-*.txt`、`results/gpu-environment.txt`。
