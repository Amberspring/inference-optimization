# 可追溯的 SLO 审计

`scripts/analyze_slo.py` 使用已保存 vLLM JSON 中的真实完成数、吞吐和 P95 TTFT/E2EL，按调用者明确指定的 SLO筛选。记录输入文件 SHA-256，不把估算值填入缺失指标，也不把缓存网关吞吐叫作 GPU 生成性能。

```sh
python scripts/analyze_slo.py results/gpu-vllm/quick/fp16-input128-c1.json results/gpu-vllm/quick/fp16-input128-c4.json results/gpu-vllm/quick/fp16-input128-c8.json results/gpu-vllm/quick/fp16-input128-c16.json --ttft-ms 200 --e2e-ms 2000 --error-rate 0.01 --output results/slo-audit-<unique-run-id>.json
```

2026-10-08 审计的是仓库保留的 **2026-10-06 历史实测文件**，不是本次重新运行 GPU。示例 SLO为 TTFT P95≤200ms、E2E P95≤2000ms、失败率≤1%，属于工程演示预算，不是业务承诺。四组同类 quick 工作负载中并发16的观测吞吐最高，为5.85 requests/s；每组仅20请求，不能据此宣称最大可持续容量。

实际部署应先确定真实业务SLO，保持模型、输入/输出长度、缓存、服务参数和硬件一致，多次更长压测后再下结论。不同长度、prefix-cache、模型或硬件结果不能混合排名；量化质量损失和长期稳定性在完成实测前保持未验证。
