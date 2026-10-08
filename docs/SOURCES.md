# 实现依据与版本

用户提供的小红书截图只用于确定项目范围；其中简历数字未用于本项目结果。

- Qwen3-8B 模型与非思考模板：https://huggingface.co/Qwen/Qwen3-8B
- TRL 0.19.1 SFT 参数：https://github.com/huggingface/trl/blob/v0.19.1/trl/trainer/sft_config.py
- TRL 0.19.1 DPO 与双适配器参考：https://huggingface.co/docs/trl/v0.19.1/en/dpo_trainer
- PEFT：https://huggingface.co/docs/peft/index
- FAISS：https://github.com/facebookresearch/faiss
- FlagEmbedding：https://github.com/FlagOpen/FlagEmbedding
- vLLM：https://docs.vllm.ai/en/latest/
- llm-compressor 0.13.0 AWQ 参考：https://github.com/vllm-project/llm-compressor/blob/0.13.0/examples/awq/llama_example.py
- llm-compressor GPTQ 与 W8A8 参考：https://docs.vllm.ai/projects/llm-compressor/en/latest/examples/

训练库在本机已使用小型随机 Qwen3 做 CPU 集成验证。vLLM、量化和 BGE 预训练模型只完成接口实现与源码参考，没有执行硬件实验。GPU 推理与量化使用独立环境，避免与训练库的依赖版本互相覆盖。
