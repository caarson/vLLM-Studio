from __future__ import annotations

from typing import Dict, List


class SettingField:
    def __init__(self, key: str, field_type: str, default, description: str, choices: List[str] | None = None):
        self.key = key
        self.field_type = field_type
        self.default = default
        self.description = description
        self.choices = choices

    def to_dict(self) -> Dict:
        return {
            "key": self.key,
            "type": self.field_type,
            "default": self.default,
            "description": self.description,
            "choices": self.choices,
        }


GROUPS: List[Dict] = [
    {
        "group": "Model & System",
        "fields": [
            SettingField("model", "string", "", "Hugging Face repo id for the base model"),
            SettingField("revision", "string", None, "Optional revision/branch/tag"),
            SettingField("download_dir", "string", "/hf-cache", "Cache directory shared across models"),
            SettingField("worker_use_ray", "boolean", False, "Enable multi-node Ray workers"),
            SettingField("enforce_eager", "boolean", False, "Run vLLM in eager mode"),
        ],
    },
    {
        "group": "Context & KV Cache",
        "fields": [
            SettingField("max_model_len", "integer", 32768, "Maximum sequence length"),
            SettingField("gpu_memory_utilization", "number", 0.9, "Fraction of GPU memory to allocate"),
            SettingField("swap_space", "integer", 8, "CPU swap space in GB for KV cache"),
            SettingField("tensor_parallel_size", "integer", 1, "Tensor parallel shards"),
            SettingField("pipeline_parallel_size", "integer", 1, "Pipeline parallel stages"),
            SettingField("kv_cache_dtype", "string", "fp8", "KV cache dtype"),
            SettingField("chunked_prefill_size", "integer", 4096, "Prefill chunk size"),
            SettingField("disable_log_stats", "boolean", False, "Disable request latency statistics"),
        ],
    },
    {
        "group": "Quant/Precision",
        "fields": [
            SettingField("dtype", "string", "float16", "Computation dtype", ["float16", "bfloat16", "float32", "auto"]),
            SettingField("quantization", "string", None, "Quantization mode (awq, gptq, gguf, etc.)"),
            SettingField("max_seq_len_to_capture", "integer", 4096, "Sequence length for CUDA graph capture"),
            SettingField("flash_attn", "boolean", True, "Enable FlashAttention"),
            SettingField("attention_backend", "string", "auto", "Attention backend override"),
        ],
    },
    {
        "group": "Serving",
        "fields": [
            SettingField("host", "string", "0.0.0.0", "API binding host"),
            SettingField("port", "integer", 8001, "API port"),
            SettingField("served_model_name", "string", None, "Override served model name"),
            SettingField("http_headers", "object", {}, "Custom HTTP headers"),
            SettingField("cors", "string", None, "Comma-separated allowed origins"),
        ],
    },
    {
        "group": "LoRA/PEFT",
        "fields": [
            SettingField("lora_modules", "list", [], "Paths to LoRA adapters"),
            SettingField("max_lora_rank", "integer", 64, "Maximum LoRA rank"),
            SettingField("enable_lora", "boolean", False, "Enable LoRA support"),
            SettingField("lora_scaling", "number", 1.0, "LoRA scaling factor"),
        ],
    },
    {
        "group": "SFT/Speculative",
        "fields": [
            SettingField("speculative_model", "string", None, "Speculative decoding draft model"),
            SettingField("num_speculative_tokens", "integer", 0, "Number of speculative tokens"),
        ],
    },
    {
        "group": "Misc",
        "fields": [
            SettingField("tokenizer", "string", None, "Tokenizer override"),
            SettingField("trust_remote_code", "boolean", False, "Allow remote code"),
            SettingField("disable_custom_kernels", "boolean", False, "Disable custom CUDA kernels"),
        ],
    },
]


def settings_index() -> Dict[str, Dict]:
    index: Dict[str, Dict] = {}
    for group in GROUPS:
        for field in group["fields"]:
            index[field.key] = {"group": group["group"], **field.to_dict()}
    return index
