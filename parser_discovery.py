# parser_discovery.py
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime

try:
    import config as app_config
except Exception:
    app_config = None

from json_profiler import scan_json_directory
from parser_registry import load_parser_registry, match_profile_to_parser, save_generated_registry


def cluster_profiles(profiles: list[dict]) -> list[dict]:
    clusters = defaultdict(list)
    for profile in profiles:
        signature = profile.get("signature") or "UNKNOWN"
        clusters[signature].append(profile)
    out = []
    for signature, items in clusters.items():
        key_counter = Counter()
        path_counter = Counter()
        marker_counter = Counter()
        for p in items:
            key_counter.update(p.get("top_level_keys", []))
            path_counter.update(p.get("paths", []))
            marker_counter.update(p.get("type_markers", []))
        out.append({
            "cluster_id": f"cluster_{signature[:8]}",
            "signature": signature,
            "files": [p.get("file") for p in items],
            "file_count": len(items),
            "common_top_level_keys": [k for k, _ in key_counter.most_common(20)],
            "common_paths": [k for k, _ in path_counter.most_common(50)],
            "type_markers": [k for k, _ in marker_counter.most_common(20)],
            "composition_like_count_max": max([p.get("composition_like_count", 0) for p in items] or [0]),
            "versioned_reference_count_max": max([p.get("versioned_reference_count", 0) for p in items] or [0]),
        })
    out.sort(key=lambda x: x["file_count"], reverse=True)
    return out


def infer_strategy(cluster: dict) -> str:
    keys = set(cluster.get("common_top_level_keys", []))
    markers = set(str(x).upper() for x in cluster.get("type_markers", []))
    if "ehr_id" in keys and "compositions" in keys and "VERSIONED_COMPOSITION" in markers:
        return "ehr_index_reference"
    if cluster.get("composition_like_count_max", 0) > 0:
        return "recursive_composition_search"
    if "VERSIONED_COMPOSITION" in markers:
        return "versioned_composition"
    return "recursive_fallback"


def infer_parser_candidate(cluster: dict) -> dict:
    strategy = infer_strategy(cluster)
    raw = json.dumps({"keys": cluster.get("common_top_level_keys", []), "paths": cluster.get("common_paths", [])}, sort_keys=True)
    suffix = hashlib.md5(raw.encode("utf-8")).hexdigest()[:8]
    json_type = f"auto_{strategy}_{suffix}"
    confidence = 0.70 if strategy != "recursive_fallback" else 0.45
    return {
        "description": "Auto-generated parser candidate from dataset scan",
        "status": "candidate" if confidence < 0.85 else "ready",
        "confidence": confidence,
        "source_cluster_id": cluster.get("cluster_id"),
        "detection": {
            "required_top_level_keys": cluster.get("common_top_level_keys", [])[:8],
            "observed_type_markers": cluster.get("type_markers", []),
        },
        "strategy": strategy,
        "observed_paths": cluster.get("common_paths", [])[:50],
        "file_count": cluster.get("file_count", 0),
        "json_type": json_type,
    }


def scan_dataset_for_parsers(folder: Path, sample_limit: int | None = None, recursive: bool = True) -> dict:
    sample_limit = sample_limit if sample_limit is not None else getattr(app_config, "PARSER_DISCOVERY_SAMPLE_LIMIT", 200)
    profiles = scan_json_directory(folder, sample_limit=sample_limit, recursive=recursive)
    registry = load_parser_registry()

    detected = []
    unknown_profiles = []
    for profile in profiles:
        match = match_profile_to_parser(profile, registry)
        item = {
            "file": profile.get("file"),
            "signature": profile.get("signature"),
            "json_type": match.get("json_type"),
            "confidence": match.get("confidence"),
            "matched_rules": match.get("matched_rules", []),
            "load_error": profile.get("load_error"),
        }
        detected.append(item)
        if match.get("json_type") == "unknown" or match.get("confidence", 0.0) < getattr(app_config, "PARSER_CONFIDENCE_CANDIDATE", 0.60):
            unknown_profiles.append(profile)

    clusters = cluster_profiles(unknown_profiles)
    candidates = [infer_parser_candidate(c) for c in clusters]

    generated_registry = {
        "version": "1.0",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "source_folder": str(folder),
        "parsers": {c["json_type"]: {k: v for k, v in c.items() if k != "json_type"} for c in candidates},
    }
    return {
        "profiles": profiles,
        "detected": detected,
        "unknown_clusters": clusters,
        "generated_registry": generated_registry,
    }


def generate_and_save_parser_registry(folder: Path, sample_limit: int | None = None, recursive: bool = True) -> dict:
    result = scan_dataset_for_parsers(folder, sample_limit=sample_limit, recursive=recursive)
    save_generated_registry(result["generated_registry"])
    return result


def summarize_detected_json_types(detected: list[dict]) -> list[dict]:
    grouped = defaultdict(list)
    for item in detected:
        grouped[item.get("json_type", "unknown")].append(item)
    rows = []
    for json_type, items in grouped.items():
        rows.append({
            "json_type": json_type,
            "files": len(items),
            "avg_confidence": round(sum(i.get("confidence", 0.0) for i in items) / max(1, len(items)), 4),
            "sample_file": items[0].get("file"),
        })
    rows.sort(key=lambda x: x["files"], reverse=True)
    return rows
