# config.py

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# -----------------------------
# UI / design system
# -----------------------------
STYLES_DIR = BASE_DIR / "styles"
CUSTOM_CSS_FILE = STYLES_DIR / "custom.css"
DEFAULT_THEME_MODE = "light"
ENABLE_MODERN_UI = True
ENABLE_DARK_MODE_TOGGLE = True

# -----------------------------
# Data / cache
# -----------------------------
DATA_DIR = BASE_DIR / "dataset/orbda1"
CACHE_DIR = BASE_DIR / ".cache"

SCHEMA_UNION_FILE = CACHE_DIR / "schema_union.json"
FIELDS_FILE = CACHE_DIR / "fields.json"

# -----------------------------
# Query execution defaults
# -----------------------------
DEFAULT_SLICE_SIZE = 200
DEFAULT_RESULT_LIMIT = 100
DEFAULT_OCCURRENCE_SEMANTICS = "ALL"

# -----------------------------
# Schema overview graph config
# -----------------------------
# Tree height:
# 1 = composition only
# 2 = composition -> entry groups
# 3 = composition -> entry groups -> subgroup paths
# 4 = composition -> entry groups -> subgroup paths -> leaf elements
#
# If < 4, subgroup nodes will show leaf counts instead of leaf nodes.
SCHEMA_OVERVIEW_MAX_DEPTH = 3

# Graph orientation:
# "LR" = horizontal (left to right)
# "TB" = vertical (top to bottom)
SCHEMA_GRAPH_DIRECTION = "TR"

# Max number of leaf nodes to show per subgroup when depth >= 4
SCHEMA_LEAF_LIMIT = 5
