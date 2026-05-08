# json_profiler.py
from __future__ import annotations

import json
import hashlib
from pathlib import Path
from typing import Any


def load_json_file(path: Path) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_path(obj: Any, dotted_path: str, default=None):
    cur = obj
    for part in dotted_path.split("."):
        if isinstance(cur, dict):
            cur = cur.get(part)
        elif isinstance(cur, list) and part.isdigit():
            idx = int(part)
            cur = cur[idx] if 0 <= idx < len(cur) else None
        else:
            return default
        if cur is None:
            return default
    return cur


def looks_like_composition(obj: Any) -> bool:
    if not isinstance(obj, dict):
        return False
    arch = obj.get("archetype_node_id", "")
    typ = obj.get("_type", obj.get("type", ""))
    if isinstance(arch, str) and "COMPOSITION" in arch:
        return True
    if isinstance(typ, str) and typ.upper() == "COMPOSITION":
        return True
    if "content" in obj and ("archetype_node_id" in obj or "name" in obj):
        return True
    return False


def collect_paths(obj: Any, prefix: str = "", max_depth: int = 8, depth: int = 0, limit: int = 3000) -> list[str]:
    paths: list[str] = []
    if depth > max_depth or len(paths) > limit:
        return paths
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = f"{prefix}.{k}" if prefix else str(k)
            paths.append(p)
            paths.extend(collect_paths(v, p, max_depth, depth + 1, limit))
            if len(paths) > limit:
                break
    elif isinstance(obj, list):
        p = f"{prefix}[]" if prefix else "[]"
        paths.append(p)
        for item in obj[:3]:
            paths.extend(collect_paths(item, p, max_depth, depth + 1, limit))
            if len(paths) > limit:
                break
    return paths[:limit]


def find_type_markers(obj: Any, markers: list[str] | None = None, max_depth: int = 8, depth: int = 0) -> list[str]:
    markers = markers or []
    if depth > max_depth:
        return markers
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in {"type", "_type", "archetype_node_id", "rm_type_name"} and isinstance(v, str):
                markers.append(v)
            find_type_markers(v, markers, max_depth, depth + 1)
    elif isinstance(obj, list):
        for item in obj[:5]:
            find_type_markers(item, markers, max_depth, depth + 1)
    return sorted(set(markers))


def count_composition_like(obj: Any, max_depth: int = 10, depth: int = 0) -> int:
    if depth > max_depth:
        return 0
    if looks_like_composition(obj):
        return 1
    if isinstance(obj, dict):
        return sum(count_composition_like(v, max_depth, depth + 1) for v in obj.values())
    if isinstance(obj, list):
        return sum(count_composition_like(x, max_depth, depth + 1) for x in obj)
    return 0


def count_versioned_refs(obj: Any, max_depth: int = 8, depth: int = 0) -> int:
    if depth > max_depth:
        return 0
    if isinstance(obj, dict):
        typ = obj.get("type") or obj.get("_type")
        here = 1 if isinstance(typ, str) and typ.upper() == "VERSIONED_COMPOSITION" and isinstance(obj.get("id"), dict) else 0
        return here + sum(count_versioned_refs(v, max_depth, depth + 1) for v in obj.values())
    if isinstance(obj, list):
        return sum(count_versioned_refs(x, max_depth, depth + 1) for x in obj)
    return 0


def compute_structure_signature(profile: dict) -> str:
    material = {
        "top_level_keys": sorted(profile.get("top_level_keys", [])),
        "major_paths": sorted(profile.get("paths", []))[:80],
        "type_markers": sorted(profile.get("type_markers", [])),
        "composition_like_count": profile.get("composition_like_count", 0),
        "versioned_reference_count": profile.get("versioned_reference_count", 0),
    }
    raw = json.dumps(material, sort_keys=True, ensure_ascii=False)
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def profile_json_obj(obj: Any, file_path: str | None = None) -> dict:
    top_keys = sorted(obj.keys()) if isinstance(obj, dict) else []
    paths = collect_paths(obj)
    array_paths = sorted({p for p in paths if "[]" in p})
    type_markers = find_type_markers(obj)
    profile = {
        "file": file_path,
        "top_level_keys": top_keys,
        "paths": sorted(set(paths)),
        "array_paths": array_paths,
        "type_markers": type_markers,
        "composition_like_count": count_composition_like(obj),
        "versioned_reference_count": count_versioned_refs(obj),
    }
    profile["signature"] = compute_structure_signature(profile)
    return profile


def profile_json_file(path: Path) -> dict:
    try:
        obj = load_json_file(path)
        profile = profile_json_obj(obj, str(path))
        profile["load_error"] = None
        return profile
    except Exception as exc:
        return {
            "file": str(path),
            "top_level_keys": [],
            "paths": [],
            "array_paths": [],
            "type_markers": [],
            "composition_like_count": 0,
            "versioned_reference_count": 0,
            "signature": "LOAD_ERROR",
            "load_error": str(exc),
        }


def scan_json_directory(folder: Path, sample_limit: int | None = None, recursive: bool = True) -> list[dict]:
    paths = folder.rglob("*.json") if recursive else folder.glob("*.json")
    profiles = []
    for idx, path in enumerate(sorted(paths)):
        if ".cache" in path.parts:
            continue
        if sample_limit is not None and idx >= sample_limit:
            break
        profiles.append(profile_json_file(path))
    return profiles
