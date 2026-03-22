# query_compiler.py

from __future__ import annotations
from typing import Dict, List, Any

def compile_query(form_state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert filled UI state into a structured query plan.

    Expected form_state format:
    {
      "criteria": [
        {
          "field_key": "...",
          "operator": "=",
          "value": "SÃO PAULO"
        }
      ],
      "output_fields": [
        {
          "field_key": "...",
          "name": "HCPA → General data → State",
          "dv_type": "DV_CODED_TEXT"
        }
      ],
      "sort": {
        "field_key": "...",
        "direction": "asc"
      } | None,
      "advanced": {
        "occurrence_semantics": "ALL",
        "include_unknown": False
      }
    }
    """
    plan = {
        "predicates": [],
        "outputs": [x["field_key"] for x in form_state.get("output_fields", [])],
        "sort": form_state.get("sort"),
        "advanced": form_state.get("advanced", {})
    }

    for c in form_state.get("criteria", []):
        # guard against empty criterion rows
        if not c.get("field_key"):
            continue

        plan["predicates"].append({
            "field_key": c["field_key"],
            "operator": c.get("operator"),
            "value": c.get("value")
        })

    return plan
