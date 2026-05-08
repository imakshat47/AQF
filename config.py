# config.py
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# -----------------------------
# Data / cache
# -----------------------------
DATA_DIR = BASE_DIR / "orbda_10k/data"
CACHE_DIR = BASE_DIR / ".cache"
SCHEMA_UNION_FILE = CACHE_DIR / "schema_union.json"
FIELDS_FILE = CACHE_DIR / "fields.json"

# -----------------------------
# Query execution defaults
# -----------------------------
DEFAULT_SLICE_SIZE = 12000
DEFAULT_RESULT_LIMIT = 12000
DEFAULT_OCCURRENCE_SEMANTICS = "ALL"

# -----------------------------
# Schema overview graph config
# -----------------------------
SCHEMA_OVERVIEW_MAX_DEPTH = 4
SCHEMA_GRAPH_DIRECTION = "TB"  # valid values: LR, TB, RL, BT
SCHEMA_LEAF_LIMIT = 5

# -----------------------------
# EHR / record-unit support
# -----------------------------
RECORD_UNITS_CACHE_DIR = CACHE_DIR / "record_units"
RECORD_UNITS_MANIFEST_FILE = CACHE_DIR / "record_units_manifest.json"
DEFAULT_INPUT_MODE = "auto"  # auto | composition | ehr
INCLUDE_EHR_METADATA_FIELDS = True
INCLUDE_EHR_INDEX_AS_QUERYABLE_FAMILY = True
INCLUDE_UNRESOLVED_COMPOSITION_REFS = True
ENABLE_REFERENCE_RESOLUTION = True
REFERENCE_SEARCH_RECURSIVE = True
EHR_INDEX_RECORD_FAMILY = "EHR_INDEX_REFERENCE"

# -----------------------------
# Parser discovery / parser registry
# -----------------------------
PARSER_MAPPING_FILE = BASE_DIR / "parser_mappings.json"
GENERATED_PARSER_MAPPING_FILE = CACHE_DIR / "parser_mappings.generated.json"
LOCAL_PARSER_MAPPING_FILE = BASE_DIR / "parser_mappings.local.json"

ENABLE_PARSER_DISCOVERY = True
PARSER_DISCOVERY_SAMPLE_LIMIT = 12000
PARSER_CONFIDENCE_READY = 0.85
PARSER_CONFIDENCE_CANDIDATE = 0.60
ALLOW_UNKNOWN_JSON_RECURSIVE_FALLBACK = True
DEFAULT_SELECTED_JSON_TYPES = []
