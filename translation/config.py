"""
Shared configuration for the translation pipeline.
"""
from pathlib import Path

# Repository root
REPO_ROOT = Path(__file__).parent.parent

# Output artifacts (consumed by Android app via assets/)
ARTIFACTS_DIR = REPO_ROOT / "app" / "src" / "main" / "assets" / "translation"

PATTERNS_JSON = ARTIFACTS_DIR / "patterns.json"
FAISS_INDEX = ARTIFACTS_DIR / "faiss.index"
INDEX_MAP_JSON = ARTIFACTS_DIR / "index_map.json"
MINILM_ONNX = ARTIFACTS_DIR / "minilm.onnx"
T5_ONNX = ARTIFACTS_DIR / "t5_asl.onnx"

# Data / model cache (not checked in)
CACHE_DIR = REPO_ROOT / ".translation_cache"
MODEL_CACHE = CACHE_DIR / "models"
DATA_CACHE = CACHE_DIR / "data"
CHECKPOINTS_DIR = CACHE_DIR / "checkpoints"

# Tier 2 parameters
MINILM_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIM = 384
VECTOR_CONFIDENCE_THRESHOLD = 0.75  # cosine similarity — must match Kotlin
FAISS_TOP_K = 3

# Tier 3 parameters
T5_BASE_MODEL = "t5-small"
T5_MAX_INPUT_LEN = 64
T5_MAX_OUTPUT_LEN = 32
T5_BATCH_SIZE = 16
T3_CONFIDENCE_THRESHOLD = 0.75  # minimum data for tier 3 to ship

# Cascade thresholds
TIER1_CONFIDENCE = 1.0   # exact match = full confidence
TIER2_MIN_CONFIDENCE = 0.6  # below this, fall through to tier 3

# Evaluation
EVAL_SPLIT = 0.1  # fraction of data held out for eval


def ensure_dirs() -> None:
    for d in [ARTIFACTS_DIR, CACHE_DIR, MODEL_CACHE, DATA_CACHE, CHECKPOINTS_DIR]:
        d.mkdir(parents=True, exist_ok=True)
