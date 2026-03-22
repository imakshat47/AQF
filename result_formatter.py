# result_formatter.py

from __future__ import annotations
from typing import Dict, List, Any
import pandas as pd

def build_short_header(label: str) -> str:
    """
    Convert long semantic labels into shorter table headers.
    Example:
      'HCPA → General data → State' -> 'State'
    """
    if not label:
        return "Field"
    parts = [p.strip() for p in label.split("→")]   #   'HCPA → chemotherapy → duration of treatment' -> 'Duration of treatment'
    
    if not parts:
        return label

    short = parts[-1]
    if short:
        short = short[0].upper() + short[1:]

    return short


def build_unique_headers(output_fields: List[Dict[str, Any]]) -> Dict[str, str]:
    """
    Create human-readable unique headers for result columns.

    Expected output_fields format:
    [
      {
        "field_key": "...",
        "name": "HCPA → General data → State",
        "dv_type": "DV_CODED_TEXT"
      },
      ...
    ]
    """
    short_headers = {}
    counts = {}

    for f in output_fields:
        label = f.get("name", "")
        short = build_short_header(label)

        counts[short] = counts.get(short, 0) + 1
        short_headers[f["field_key"]] = short

    final_headers = {}
    for f in output_fields:
        label = f.get("name", "")
        short = build_short_header(label)

        if counts[short] > 1:
            # If duplicate short headers exist, expand with fuller semantic path
            full = label.replace(" → ", " / ")
            final_headers[f["field_key"]] = full
        else:
            final_headers[f["field_key"]] = short

    return final_headers


def format_cell_value(v: Any) -> str:
    """
    Make result cell values user-friendly.
    """
    if v is None:
        return "—"

    if isinstance(v, list):
        clean = [format_cell_value(x) for x in v if x is not None]
        if not clean:
            return "—"
        return ", ".join(dict.fromkeys(clean))  # dedupe while preserving order

    s = str(v).strip()

    if s == "":
        return "—"

    if s.lower() == "unknown":
        return "Unknown"

    return s


def format_results_for_display(rows: List[Dict[str, Any]], output_fields: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Convert raw query result rows into a display-friendly dataframe.

    rows format:
    [
      {
        "_file": "...json",
        "<field_key_1>": "SÃO PAULO",
        "<field_key_2>": "60.0"
      }
    ]

    output_fields format:
    [
      {
        "field_key": "...",
        "name": "HCPA → General data → State",
        "dv_type": "DV_CODED_TEXT"
      }
    ]
    """
    if not rows:
        return pd.DataFrame()

    header_map = build_unique_headers(output_fields)

    formatted_rows = []
    for idx, row in enumerate(rows, start=1):
        new_row = {
            "Record": f"Record {idx}"
        }

        if "_file" in row:
            new_row["_source_file"] = row["_file"]

        for key, value in row.items():
            if key == "_file":
                continue

            display_col = header_map.get(key, key)
            new_row[display_col] = format_cell_value(value)

        formatted_rows.append(new_row)

    df = pd.DataFrame(formatted_rows)

    cols = list(df.columns)
    ordered = ["Record"] + [c for c in cols if c not in ("Record", "_source_file")]
    if "_source_file" in df.columns:
        ordered.append("_source_file")

    return df[ordered]
    

