# parser_registry.py
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    import config as app_config
except Exception:
    app_config = None


def load_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(obj: dict, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)


def normalize_registry(registry: dict | None) -> dict:
    if not registry:
        return {"version": "1.0", "parsers": {}}
    if "parsers" in registry:
        return registry
    # Backward compatibility: old format was {json_type: mapping}
    return {"version": "1.0", "parsers": registry}


def merge_parser_registries(*registries: dict) -> dict:
    merged = {"version": "1.0", "parsers": {}}
    for reg in registries:
        norm = normalize_registry(reg)
        merged["parsers"].update(norm.get("parsers", {}))
    return merged


def load_parser_registry() -> dict:
    registries = []
    for attr in ["PARSER_MAPPING_FILE", "GENERATED_PARSER_MAPPING_FILE", "LOCAL_PARSER_MAPPING_FILE"]:
        path = getattr(app_config, attr, None) if app_config else None
        if path and Path(path).exists():
            try:
                registries.append(load_json(Path(path)))
            except Exception:
                pass
    return merge_parser_registries(*registries)


def save_generated_registry(registry: dict):
    path = getattr(app_config, "GENERATED_PARSER_MAPPING_FILE", Path(".cache/parser_mappings.generated.json")) if app_config else Path(".cache/parser_mappings.generated.json")
    save_json(registry, Path(path))


def _top_key_score(profile: dict, detection: dict) -> float:
    top = set(profile.get("top_level_keys", []))
    required = set(detection.get("required_top_level_keys", []))
    any_keys = set(detection.get("any_top_level_keys", []))
    score = 0.0
    if required:
        score += len(top & required) / max(1, len(required))
    if any_keys:
        score += 1.0 if top & any_keys else 0.0
    if not required and not any_keys:
        score += 0.5
    return min(score, 1.0)


def _marker_score(profile: dict, detection: dict) -> float:
    markers = set(str(x).upper() for x in profile.get("type_markers", []))
    score = 0.0
    equals = detection.get("equals", {})
    contains = detection.get("contains", {})
    for _path, expected in equals.items():
        if str(expected).upper() in markers:
            score += 1.0
    for _path, expected in contains.items():
        if any(str(expected).upper() in m for m in markers):
            score += 1.0
    if detection.get("min_composition_like_count"):
        score += 1.0 if profile.get("composition_like_count", 0) >= detection.get("min_composition_like_count", 1) else 0.0
    return min(score, 1.0)


def _array_shape_score(profile: dict, detection: dict) -> float:
    # Lightweight support for common EHR index reference detection.
    array_conditions = detection.get("array_item_equals", {})
    if not array_conditions:
        return 0.5
    markers = set(str(x).upper() for x in profile.get("type_markers", []))
    matched = 0
    total = 0
    for _array_path, conditions in array_conditions.items():
        for _field, expected in conditions.items():
            total += 1
            if str(expected).upper() in markers:
                matched += 1
    return matched / max(1, total)


def match_profile_to_parser(profile: dict, registry: dict | None = None) -> dict:
    registry = normalize_registry(registry or load_parser_registry())
    best = {"json_type": "unknown", "confidence": 0.0, "parser": None, "matched_rules": []}
    for json_type, parser in registry.get("parsers", {}).items():
        detection = parser.get("detection", {})
        key_score = _top_key_score(profile, detection)
        marker_score = _marker_score(profile, detection)
        array_score = _array_shape_score(profile, detection)
        confidence = 0.40 * key_score + 0.40 * marker_score + 0.20 * array_score
        if confidence > best["confidence"]:
            best = {
                "json_type": json_type,
                "confidence": round(confidence, 4),
                "parser": parser,
                "matched_rules": [
                    f"top_keys={key_score:.2f}",
                    f"markers={marker_score:.2f}",
                    f"arrays={array_score:.2f}",
                ],
            }
    return best


def validate_mapping(mapping: dict) -> list[str]:
    errors = []
    if "strategy" not in mapping:
        errors.append("Missing parser strategy")
    if "detection" not in mapping:
        errors.append("Missing detection rules")
    return errors
