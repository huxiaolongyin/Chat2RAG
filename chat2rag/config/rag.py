import os

_load_str_env = lambda name: os.environ.get(name)
_load_int_env = lambda name: int(os.environ.get(name)) if os.environ.get(name) else None
_load_float_env = lambda name: float(os.environ.get(name)) if os.environ.get(name) else None
_load_bool_env = lambda name: os.environ.get(name) and os.environ.get(name).lower() in [
    "true",
    "1",
    "yes",
]

EMBEDDING_OPENAI_URL = _load_str_env("EMBEDDING_OPENAI_URL")
EMBEDDING_MODEL = _load_str_env("EMBEDDING_MODEL") or "360Zhinao-search"
EMBEDDING_DIMENSIONS = _load_int_env("EMBEDDING_DIMENSIONS") or 1024
EMBEDDING_API_KEY = _load_str_env("EMBEDDING_API_KEY")

QDRANT_LOCATION = _load_str_env("QDRANT_LOCATION") or "http://localhost/6333"

TOP_K = _load_int_env("TOP_K") or 5
SCORE_THRESHOLD = _load_float_env("SCORE_THRESHOLD") or 0.65
PRECISION_MODE = _load_bool_env("PRECISION_MODE") or False
PRECISION_THRESHOLD = _load_float_env("PRECISION_THRESHOLD") or 0.88

RETRIEVAL_MODE = _load_str_env("RETRIEVAL_MODE") or "hybrid"

SPARSE_MODEL_PATH = _load_str_env("SPARSE_MODEL_PATH")
