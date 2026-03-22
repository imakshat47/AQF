# composition_loader.py

from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, List, Tuple
from utils import safe_get

def list_json_files(folder: Path) -> List[Path]:
    return sorted([p for p in folder.iterdir() if p.suffix.lower() == ".json"])

def load_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def classify_file(doc: dict) -> Tuple[str, str]:
    """
    Return (family, reason)
    family:
      - COMPOSITION_VERSION
      - EHR_INDEX
      - UNKNOWN
    """
    # Composition docs
    arch = safe_get(doc, ["versions", "data", "archetype_node_id"])
    content = safe_get(doc, ["versions", "data", "content"])
    if isinstance(arch, str) and isinstance(content, list):
        return "COMPOSITION_VERSION", "versions.data.archetype_node_id + versions.data.content[] present"

    # EHR index / summary docs
    if "ehr_id" in doc and (isinstance(doc.get("compositions"), list) or isinstance(doc.get("contributions"), list)):
        return "EHR_INDEX", "ehr_id + compositions/contributions present"

    return "UNKNOWN", "Not recognized as composition version"

def get_composition_archetype(doc: dict) -> str:
    return safe_get(doc, ["versions", "data", "archetype_node_id"], "UNKNOWN_COMPOSITION")

def get_composition_label(doc: dict) -> str:
    return safe_get(doc, ["versions", "data", "name", "value"], "Unknown composition")

def group_docs_by_composition_archetype(folder: Path):
    """
    Returns:
      valid_groups: {comp_arch: [(path, doc), ...]}
      skipped: [{"file": ..., "family": ..., "reason": ...}, ...]

    We skip non-composition docs for the first implementation because the
    accordion-form UI is composition-family specific. Non-composition files
    are surfaced in diagnostics instead of breaking the union build.
    """
    valid_groups: Dict[str, List[Tuple[Path, dict]]] = {}
    skipped: List[Dict] = []

    for fp in list_json_files(folder):
        try:
            doc = load_json(fp)
        except Exception as e:
            skipped.append({
                "file": str(fp.name),
                "family": "INVALID_JSON",
                "reason": f"Failed to parse JSON: {e}"
            })
            continue

        family, reason = classify_file(doc)

        if family == "COMPOSITION_VERSION":
            arch = get_composition_archetype(doc)
            valid_groups.setdefault(arch, []).append((fp, doc))
        else:
            skipped.append({
                "file": str(fp.name),
                "family": family,
                "reason": reason
            })

    return valid_groups, skipped