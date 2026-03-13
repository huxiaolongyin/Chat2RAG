import os

_load_str_env = lambda name: os.environ.get(name)

MODEL = _load_str_env("MODEL") or "Qwen3-32B"
PROCESS_MODEL = MODEL
DEFAULT_MODEL = MODEL

GENERATION_KWARGS = {
    "temperature": 0.15,
    "presence_penalty": -0.5,
    "frequency_penalty": -0.5,
    "top_p": 0.95,
    "seed": 1234,
    "extra_body": {
        "stream_options": {"include_usage": True},
    },
}

MODEL_LIST = [
    {
        "name": "DeepSeek-V3.2",
        "id": "Pro/deepseek-ai/DeepSeek-V3.2",
        "generation_kwargs": {
            "extra_body": {"enable_thinking": False, "thinking_budget": 100}
        },
    },
    {"name": "Deepseek-v3", "id": "Pro/deepseek-ai/DeepSeek-V3"},
    {"name": "Qwen2.5-32B", "id": "Qwen/Qwen2.5-32B-Instruct"},
    {"name": "Qwen2.5-72B", "id": "Qwen/Qwen2.5-72B-Instruct"},
    {
        "name": "Qwen3-32B",
        "id": "Qwen/Qwen3-32B",
        "generation_kwargs": {
            "extra_body": {"enable_thinking": False, "thinking_budget": 100}
        },
    },
    {"name": "Qwen3-235B", "id": "Qwen/Qwen3-235B-A22B-Instruct-2507"},
    {"name": "DeepSeek-V3.1", "id": "Pro/deepseek-ai/DeepSeek-V3.1-Terminus"},
]

CHAT_V1_DEFAULT_MODELS = {
    "intention": "Qwen2.5-14B",
    "generator": "Qwen2.5-32B",
}
