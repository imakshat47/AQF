# config.py

from pathlib import Path

# Root paths
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "dataset/orbda1"
CACHE_DIR = BASE_DIR / ".cache"

# Cache files
SCHEMA_UNION_FILE = CACHE_DIR / "schema_union.json"
FIELDS_FILE = CACHE_DIR / "fields.json"

# Query execution defaults
DEFAULT_SLICE_SIZE = 200
DEFAULT_RESULT_LIMIT = 100

# Accordion UI behavior
DEFAULT_EXPANDED_GROUPS = ["HCPA"]
# , "Problem/Diagnosis"

# Repeated field semantics (first build default)
DEFAULT_OCCURRENCE_SEMANTICS = "ALL"  # later can support ANY
