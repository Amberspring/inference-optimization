# 业务负载容量协议（冻结草案）

正式输入直接使用电商项目独立 AmazonQA 200 题文件的 `prompt`，不再用随机 token 或六条合成中文问题代表业务分布。输入文件、模型权重、服务启动命令和结果目录都记录 SHA-256；同一模型、`temperature=0`、`max_tokens=256` 下比较配置，截断和接口错误计入失败。

容量测试采用恒定到达率开放环路，而不是请求完成后才发送下一批的闭环并发。每个候选到达率预热 10 个请求，然后独立运行 3 次，每次 300 秒；客户端最多保留 64 个在途请求，超过时记录 `client_overflow`，不得静默删掉。每次保存逐请求 TTFT、完整响应时间、HTTP 状态、输出、finish reason、usage 和 prompt 哈希，并报告 P50/P95/P99、错误率、实际吞吐与输出 token/s。

初始到达率从历史稳定观测值以下开始，逐级增加，直到连续三次中任一次越过预先采用的 SLO：P95 TTFT 200ms、P95 完整响应 2000ms、错误率 1%。这只是本项目展示目标，不是行业统一标准；若 256 token 的真实业务请求无法达到，则报告最大实测稳定档位和失败边界，不缩短答案来把结果变绿。Prefix cache 开关必须分别启动服务并记录，不能把缓存开启与关闭的结果混算。

示例命令：

```sh
python scripts/benchmark_open_loop.py --model ecommerce-dpo --workload ../ecommerce-alignment/artifacts/amazonqa-audit-20261010/eval.jsonl --server-manifest results/business-load-20261010/server.json --request-rate 1 --duration 300 --repeats 3 --max-tokens 256 --output results/business-load-20261010/rate-1
```
