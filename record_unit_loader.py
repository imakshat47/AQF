# record_unit_loader.py
from __future__ import annotations

import json
import hashlib
from pathlib import Path
from typing import Any

try:
    import config as app_config
except Exception:
    app_config = None

try:
    from json_profiler import profile_json_obj
    from parser_registry import load_parser_registry, match_profile_to_parser
except Exception:
    profile_json_obj = None
    load_parser_registry = None
    match_profile_to_parser = None


def load_json_file(path: Path) -> dict | list:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_path(obj: Any, path: str, default=None):
    cur = obj
    for part in path.split("."):
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


def is_versioned_composition_reference(obj: Any) -> bool:
    if not isinstance(obj, dict):
        return False
    typ = obj.get("type") or obj.get("_type")
    return isinstance(typ, str) and typ.upper() == "VERSIONED_COMPOSITION" and isinstance(obj.get("id"), dict)


def is_ehr_index_reference(obj: Any) -> bool:
    if not isinstance(obj, dict):
        return False
    comps = obj.get("compositions")
    if "ehr_id" not in obj or not isinstance(comps, list) or not comps:
        return False
    return all(is_versioned_composition_reference(c) for c in comps if isinstance(c, dict))


def fallback_detect_json_type(obj: Any) -> str:
    if looks_like_composition(obj):
        return "inline_composition"
    if is_ehr_index_reference(obj):
        return "ehr_index_reference"
    if isinstance(obj, dict):
        typ = obj.get("type") or obj.get("_type")
        if isinstance(typ, str) and typ.upper() == "VERSIONED_COMPOSITION":
            return "versioned_composition"
        if "ehr_id" in obj and recursive_find_compositions(obj):
            return "ehr_with_inline_compositions"
    return "unknown"


def detect_json_type(obj: Any, file_path: str | None = None) -> tuple[str, float]:
    if profile_json_obj and load_parser_registry and match_profile_to_parser:
        try:
            profile = profile_json_obj(obj, file_path)
            match = match_profile_to_parser(profile, load_parser_registry())
            if match.get("confidence", 0.0) >= getattr(app_config, "PARSER_CONFIDENCE_CANDIDATE", 0.60):
                return match.get("json_type", "unknown"), match.get("confidence", 0.0)
        except Exception:
            pass
    return fallback_detect_json_type(obj), 1.0


def extract_archetype_id(composition: dict) -> str:
    arch = composition.get("archetype_node_id")
    if arch:
        return arch
    details = composition.get("archetype_details", {})
    if isinstance(details, dict):
        aid = details.get("archetype_id", {})
        if isinstance(aid, dict):
            return aid.get("value", "UNKNOWN_COMPOSITION")
        if isinstance(aid, str):
            return aid
    return "UNKNOWN_COMPOSITION"


def extract_name(obj: dict) -> str:
    name = obj.get("name")
    if isinstance(name, dict):
        return name.get("value", "")
    if isinstance(name, str):
        return name
    return ""


def extract_uid(obj: dict) -> str:
    uid = obj.get("uid")
    if isinstance(uid, dict):
        return uid.get("value", "")
    if isinstance(uid, str):
        return uid
    return ""


def recursive_find_compositions(obj: Any) -> list[dict]:
    found = []
    if looks_like_composition(obj):
        found.append(obj)
        return found
    if isinstance(obj, dict):
        for value in obj.values():
            found.extend(recursive_find_compositions(value))
    elif isinstance(obj, list):
        for item in obj:
            found.extend(recursive_find_compositions(item))
    return found


def extract_ehr_id(obj: dict) -> str | None:
    for candidate in [obj.get("ehr_id"), obj.get("ehrId"), obj.get("id")]:
        if isinstance(candidate, str):
            return candidate
        if isinstance(candidate, dict):
            value = candidate.get("value") or candidate.get("id")
            if value:
                return value
    ehr = obj.get("ehr")
    if isinstance(ehr, dict):
        return extract_ehr_id(ehr)
    return None


def extract_subject_id(obj: dict) -> str | None:
    for key in ["subject_id", "subjectId", "patient_id", "patientId"]:
        value = obj.get(key)
        if isinstance(value, str):
            return value
    subject = obj.get("subject")
    if isinstance(subject, dict):
        external_ref = subject.get("external_ref", {})
        if isinstance(external_ref, dict):
            ref_id = external_ref.get("id", {})
            if isinstance(ref_id, dict):
                return ref_id.get("value")
            if isinstance(ref_id, str):
                return ref_id
    ehr_status = obj.get("ehr_status") or obj.get("ehrStatus")
    if isinstance(ehr_status, dict):
        return extract_subject_id(ehr_status)
    return None


def make_unit_id(source_file: Path, index: int, composition: dict) -> str:
    raw = f"{source_file}|{index}|{extract_uid(composition)}|{extract_archetype_id(composition)}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def make_composition_unit(composition: dict, source_file: Path, index: int = 0, ehr_id: str | None = None, subject_id: str | None = None, ehr_context: dict | None = None, json_type: str | None = None) -> dict:
    family = extract_archetype_id(composition)
    return {
        "unit_id": make_unit_id(source_file, index, composition),
        "source_file": str(source_file),
        "ehr_id": ehr_id,
        "subject_id": subject_id,
        "record_family": family,
        "composition_archetype": family,
        "composition_name": extract_name(composition),
        "composition_uid": extract_uid(composition),
        "json_type": json_type,
        "raw_composition": composition,
        "ehr_context": ehr_context or {"ehr_id": ehr_id, "subject_id": subject_id, "source_file": str(source_file)},
    }


def make_metadata_item(label: str, value: Any, node_id: str) -> dict:
    return {"archetype_node_id": node_id, "name": {"value": label}, "value": {"value": value}}


def parse_ehr_index_reference(obj: dict, source_file: Path, json_type: str = "ehr_index_reference") -> list[dict]:
    ehr_id = get_path(obj, "ehr_id.value") or extract_ehr_id(obj)
    system_id = get_path(obj, "system_id.value")
    time_created = get_path(obj, "time_created.value")
    compositions = obj.get("compositions", []) if isinstance(obj.get("compositions"), list) else []
    contributions = obj.get("contributions", []) if isinstance(obj.get("contributions"), list) else []
    family = getattr(app_config, "EHR_INDEX_RECORD_FAMILY", "EHR_INDEX_REFERENCE") if app_config else "EHR_INDEX_REFERENCE"
    raw = {
        "archetype_node_id": family,
        "name": {"value": "EHR Index Reference"},
        "content": [{
            "archetype_node_id": "AQF-EHR-METADATA",
            "name": {"value": "EHR metadata"},
            "items": [
                make_metadata_item("System ID", system_id, "aqf.ehr.system_id"),
                make_metadata_item("EHR ID", ehr_id, "aqf.ehr.ehr_id"),
                make_metadata_item("Time created", time_created, "aqf.ehr.time_created"),
                make_metadata_item("Contribution count", len(contributions), "aqf.ehr.contribution_count"),
                make_metadata_item("Composition reference count", len(compositions), "aqf.ehr.composition_count"),
            ],
        }],
        "_aqf_metadata": {
            "system_id": system_id,
            "ehr_id": ehr_id,
            "time_created": time_created,
            "contribution_count": len(contributions),
            "composition_count": len(compositions),
            "composition_refs": compositions,
            "ehr_access": obj.get("ehr_access"),
            "ehr_status": obj.get("ehr_status"),
        },
    }
    unit_id = hashlib.md5(f"{source_file}|ehr_index|{ehr_id}".encode("utf-8")).hexdigest()
    return [{
        "unit_id": unit_id,
        "source_file": str(source_file),
        "ehr_id": ehr_id,
        "subject_id": None,
        "record_family": family,
        "composition_archetype": family,
        "composition_name": "EHR Index Reference",
        "composition_uid": ehr_id or unit_id,
        "json_type": json_type,
        "raw_composition": raw,
        "ehr_context": {"system_id": system_id, "ehr_id": ehr_id, "time_created": time_created, "source_file": str(source_file), "composition_refs": compositions},
        "unresolved_composition_refs": compositions,
    }]


def build_file_index(folder: Path) -> dict[str, Path]:
    recursive = getattr(app_config, "REFERENCE_SEARCH_RECURSIVE", True) if app_config else True
    paths = folder.rglob("*.json") if recursive else folder.glob("*.json")
    index = {}
    for path in paths:
        if ".cache" in path.parts:
            continue
        index[path.stem] = path
        index[path.name] = path
    return index


def resolve_composition_reference(ref: dict, file_index: dict[str, Path]) -> Path | None:
    id_value = get_path(ref, "id.value")
    if not id_value:
        return None
    for candidate in [id_value, f"{id_value}.json"]:
        if candidate in file_index:
            return file_index[candidate]
    for key, path in file_index.items():
        if id_value in key:
            return path
    return None


def unwrap_versioned_composition(obj: Any) -> dict | None:
    if looks_like_composition(obj):
        return obj
    candidate_paths = [["data"], ["version", "data"], ["versions", 0, "data"], ["items", 0, "data"], ["composition"]]
    for path in candidate_paths:
        cur = obj
        ok = True
        for part in path:
            if isinstance(part, int):
                if isinstance(cur, list) and len(cur) > part:
                    cur = cur[part]
                else:
                    ok = False
                    break
            else:
                if isinstance(cur, dict) and part in cur:
                    cur = cur[part]
                else:
                    ok = False
                    break
        if ok and looks_like_composition(cur):
            return cur
    found = recursive_find_compositions(obj)
    return found[0] if found else None


def parse_ehr_index_with_resolution(obj: dict, source_file: Path, root_folder: Path, json_type: str = "ehr_index_reference") -> tuple[list[dict], list[dict]]:
    units = parse_ehr_index_reference(obj, source_file, json_type=json_type)
    skipped = []
    enable_resolution = getattr(app_config, "ENABLE_REFERENCE_RESOLUTION", True) if app_config else True
    if not enable_resolution:
        return units, skipped
    ehr_id = get_path(obj, "ehr_id.value") or extract_ehr_id(obj)
    subject_id = extract_subject_id(obj)
    file_index = build_file_index(root_folder)
    resolved_refs = []
    for idx, ref in enumerate(obj.get("compositions", [])):
        resolved_path = resolve_composition_reference(ref, file_index)
        if not resolved_path or resolved_path == source_file:
            skipped.append({"file": str(source_file), "reason": f"Could not resolve composition reference {get_path(ref, 'id.value')}"})
            continue
        try:
            resolved_obj = load_json_file(resolved_path)
            composition = unwrap_versioned_composition(resolved_obj)
        except Exception as exc:
            skipped.append({"file": str(resolved_path), "reason": f"Resolved file load/unwrap failed: {exc}"})
            continue
        if not composition:
            skipped.append({"file": str(resolved_path), "reason": "Resolved file did not contain a composition body"})
            continue
        units.append(make_composition_unit(composition, resolved_path, idx, ehr_id, subject_id, {"ehr_index_file": str(source_file), "ehr_id": ehr_id, "subject_id": subject_id, "composition_ref": ref}, json_type="resolved_composition"))
        resolved_refs.append(ref)
    if units and units[0].get("record_family") == (getattr(app_config, "EHR_INDEX_RECORD_FAMILY", "EHR_INDEX_REFERENCE") if app_config else "EHR_INDEX_REFERENCE"):
        if getattr(app_config, "INCLUDE_UNRESOLVED_COMPOSITION_REFS", True) if app_config else True:
            units[0]["unresolved_composition_refs"] = [r for r in obj.get("compositions", []) if r not in resolved_refs]
        else:
            units[0]["unresolved_composition_refs"] = []
    include_index = getattr(app_config, "INCLUDE_EHR_INDEX_AS_QUERYABLE_FAMILY", True) if app_config else True
    if not include_index and units and units[0].get("record_family") == "EHR_INDEX_REFERENCE":
        units = units[1:]
    return units, skipped


def normalize_json_file(path: Path, root_folder: Path | None = None, allowed_json_types: list[str] | None = None) -> tuple[list[dict], list[dict]]:
    try:
        obj = load_json_file(path)
    except Exception as e:
        return [], [{"file": str(path), "reason": f"JSON load failed: {e}"}]
    root_folder = root_folder or path.parent
    json_type, confidence = detect_json_type(obj, str(path))
    if allowed_json_types and json_type not in allowed_json_types:
        return [], []
    if json_type == "ehr_index_reference" or json_type.startswith("auto_ehr_index_reference"):
        return parse_ehr_index_with_resolution(obj, path, root_folder, json_type=json_type)
    if json_type == "versioned_composition" or json_type.startswith("auto_versioned_composition"):
        composition = unwrap_versioned_composition(obj)
        if composition:
            return [make_composition_unit(composition, path, json_type=json_type)], []
        return [], [{"file": str(path), "reason": "VERSIONED_COMPOSITION wrapper did not contain a composition body"}]
    compositions = recursive_find_compositions(obj)
    if not compositions:
        allow_fallback = getattr(app_config, "ALLOW_UNKNOWN_JSON_RECURSIVE_FALLBACK", True) if app_config else True
        if json_type == "unknown" and not allow_fallback:
            return [], []
        return [], [{"file": str(path), "reason": f"No composition-like objects found; detected json_type={json_type}"}]
    ehr_id = extract_ehr_id(obj) if isinstance(obj, dict) else None
    subject_id = extract_subject_id(obj) if isinstance(obj, dict) else None
    return [make_composition_unit(comp, path, idx, ehr_id, subject_id, json_type=json_type) for idx, comp in enumerate(compositions)], []


def group_record_units_by_family(folder: Path, allowed_json_types: list[str] | None = None):
    groups = {}
    skipped = []
    if not folder.exists():
        return groups, [{"file": str(folder), "reason": "Folder does not exist"}]
    paths = folder.rglob("*.json") if (getattr(app_config, "REFERENCE_SEARCH_RECURSIVE", True) if app_config else True) else folder.glob("*.json")
    for path in sorted(paths):
        if ".cache" in path.parts:
            continue
        units, file_skipped = normalize_json_file(path, root_folder=folder, allowed_json_types=allowed_json_types)
        skipped.extend(file_skipped)
        for unit in units:
            groups.setdefault(unit.get("record_family", "UNKNOWN_COMPOSITION"), []).append(unit)
    return groups, skipped


def safe_family_name(family: str) -> str:
    return family.replace("/", "_").replace("\\", "_").replace(":", "_").replace(".", "_").replace(" ", "_")


def materialize_record_units(record_groups: dict, cache_dir: Path):
    materialized = {}
    for family, units in record_groups.items():
        family_dir = cache_dir / safe_family_name(family)
        family_dir.mkdir(parents=True, exist_ok=True)
        materialized[family] = []
        for unit in units:
            unit_path = family_dir / f"{unit['unit_id']}.json"
            with open(unit_path, "w", encoding="utf-8") as f:
                json.dump(unit["raw_composition"], f, indent=2, ensure_ascii=False)
            materialized[family].append((unit_path, unit))
    return materialized
