# 原帖路线：当前交付与正式验收

使用 ecommerce-alignment、financial-report-rag、inference-optimization 三个独立仓库。金融产品客服版本保留作历史，不再作为本路线项目一。

## 项目一：电商客服后训练

Qwen3-8B + TRL + PEFT；SFT rank=4/8/16/64，q/v 与全线性层、NF4 QLoRA；DPO beta=0.05/0.1/0.3。每个 DPO 从同一个 r16 SFT 产物初始化，输出目录独立。训练后检查参数确实更新、reference 未改变。

```bash
cd ecommerce-alignment
python -m pip install -e '.[gpu,eval]'
python scripts/build_synthetic.py
python scripts/ablation.py --stage sft --execute
python scripts/ablation.py --stage dpo --execute
python scripts/merge_adapter.py --adapter artifacts/dpo-beta-0.1/dpo/policy --output artifacts/merged-model
```

新示例数据为 32 个明确标记的虚构店铺、256 条问答及偏好对；按店铺隔离 160/48/48，提示包含规则，考察规则遵循。相同模板并不等于独立真实业务样本。没有声称获得原帖 5800 条真实客服数据、人工胜率或自动解决率。旧 tiny CPU 结果只验证训练机制，不能作为新语料/8B 的结果。

量化质量：对基座、各 SFT、DPO 及各量化模型依次启动 vLLM；固定生成设置运行 scripts/predict.py --model ecommerce-model --dataset data/ecommerce/eval.jsonl --output results/<variant>-predictions.jsonl，再用 python -m ecom.evaluate --dataset data/ecommerce/eval.jsonl --predictions ... --output ...。关键词规则不是人工偏好胜率。正式偏好评估需要独立盲评；不要用 chosen 构造规则自动宣布 DPO 胜出。

已完成 Qwen3-8B NF4 QLoRA SFT 与 DPO 主路径：rank=16、q_proj/v_proj、各 2 epoch，并保存训练摘要与显存峰值。尚未运行 rank/target-module 全量消融、beta 噪声对照、人工盲评及业务自动解决率。当前偏好 rejected 明显较差，正式实验需加入模型真实生成的困难负例和人工复核。

## 项目二：原帖金融研报 RAG

复用已测 RAG：PDF 表格保护、FAISS Flat/IVF/HNSW、BM25/RRF、BGE、reranker、引用拒答、badcase、数值计算、FastAPI demo。保留 FinQA 131 页和固定 dev40/test100 的 31 组真实实验，以及 168 页真实 PDF 解析记录。

原帖中文正式配置 configs/original-bge-zh.json 使用 bge-large-zh-v1.5 + bge-reranker-v2-m3。既有英文 FinQA 结果使用英文 small BGE/MiniLM，不能改名冒充中文 large BGE 结果。

```bash
cd financial-report-rag
python -m pip install -e '.[neural,bge]'
python scripts/benchmark_finqa.py --neural --reranker BAAI/bge-reranker-v2-m3 --flag-reranker
RAG_CONFIG=configs/original-bge-zh.json python -m uvicorn finrag.api:app --port 8001
```

benchmark 会覆盖对应结果，运行前备份。正式中文原帖验收还缺 200–300 份独立公开文档、80–120 条有人工证据标签的中文问题及最终答案评测；不能把 131 个 FinQA 页面写成 131 份完整研报。图扩展是用户所给 GitHub 的额外思路，不是本原帖必选技术。

## 项目三：部署与优化

训练、量化和 vLLM 使用分别的虚拟环境。量化环境安装 requirements-quantization.txt；推理环境安装 requirements-gpu.txt。每次一个模型，固定同一语料和生成设置。

```bash
cd inference-optimization
python scripts/quantize.py --model ../ecommerce-alignment/artifacts/merged-model --data ../ecommerce-alignment/artifacts/data/train.jsonl --scheme awq --samples 128 --output artifacts/awq
# 同样执行 gptq、int8，输出目录分别 artifacts/gptq、artifacts/int8
python scripts/serve_vllm.py --model ../ecommerce-alignment/artifacts/merged-model --prefix-cache off --execute
# 另一个终端
python scripts/benchmark_vllm.py --model ../ecommerce-alignment/artifacts/merged-model --label fp16 --execute
docker compose up -d redis
python scripts/benchmark_redis.py
```

对每个量化模型重复部署、质量评测和压测。原生 vLLM 压测覆盖三种输入长度及并发 1/4/8/16/32，保存逐请求 TTFT/TPOT/ITL/E2EL 和 P50/95/99；再对 prefix cache 开关及 batching 参数比较。随机 token 工作负载只测容量，客服质量另测；TTFT 不能当纯 GPU prefill 时长。gpu_monitor.py 记录整张卡占用，需保持无其他任务。Redis 单独 SET/GET 基准不等于端到端性能。

网关 BACKEND=vllm、MODEL=ecommerce-model、MODEL_URL=http://127.0.0.1:8000/v1、RAG_URL=http://127.0.0.1:8001、REDIS_URL=redis://127.0.0.1:6379/0；运行 gateway.service:app，再运行 benchmark.py 热点/非热点及 fault_drill.py。故障注入不等于真实显卡 OOM。

## 完成条件

代码、CPU 检查和已保存的 GPU 主路径结果不代表原帖全部消融已经完成。当前已保存真实训练摘要、vLLM 启动日志、并发与 prefix-cache 基准；量化质量、Redis 端到端性能、完整人工盲评和全量消融仍待运行。简历只采用仓库中可追溯的实测数字，不复制原帖或参考仓库成果。
