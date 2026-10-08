import argparse, json

p = argparse.ArgumentParser()
p.add_argument("--layers", type=int, required=True)
p.add_argument("--kv-heads", type=int, required=True)
p.add_argument("--head-dim", type=int, required=True)
p.add_argument("--tokens", type=int, required=True)
p.add_argument("--batch", type=int, default=1)
p.add_argument("--bytes", type=int, default=2)
a = p.parse_args()
# GQA uses KV head count, not total attention hidden dimension.
print(
    json.dumps(
        {
            "kv_cache_estimate_bytes": 2
            * a.layers
            * a.kv_heads
            * a.head_dim
            * a.tokens
            * a.batch
            * a.bytes,
            "scope": "formula_estimate_excludes_allocator_paging_weights_and_workspace",
        }
    )
)
