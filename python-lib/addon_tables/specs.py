from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ColumnSpec:
    name: str
    path: str
    default: str = ""


def is_non_empty_string(v: Any) -> bool:
    return isinstance(v, str) and bool(v.strip())


def get_by_path(obj: Any, path: str) -> Any:
    """Resolve a dotted path on a nested dict.

    Supported: `a.b.c` where each segment is a dict key.
    Returns None when path cannot be resolved.
    """

    if not isinstance(path, str) or not path.strip():
        return None

    cur: Any = obj
    for seg in path.split("."):
        seg = seg.strip()
        if not seg:
            return None

        if isinstance(cur, dict) and seg in cur:
            cur = cur[seg]
        else:
            return None

    return cur


def parse_spec_json(spec_json: Any) -> list[ColumnSpec]:
    """Parse the JSON spec from plugin settings.

    Expected shape:
    {
      "columns": [
        {"name": "connection_name", "path": "name", "default": ""}
      ]
    }
    """

    if not is_non_empty_string(spec_json):
        return []

    try:
        spec = json.loads(spec_json)
    except Exception as e:
        raise ValueError(f"Invalid JSON spec: {e}")

    columns = spec.get("columns") if isinstance(spec, dict) else None
    if not isinstance(columns, list):
        raise ValueError("Invalid JSON spec: expected object with key 'columns' (list)")

    out: list[ColumnSpec] = []
    seen: set[str] = set()
    for col in columns:
        if not isinstance(col, dict):
            continue
        name = col.get("name")
        path = col.get("path")
        if not is_non_empty_string(name) or not is_non_empty_string(path):
            continue
        name = str(name).strip()
        if name in seen:
            continue
        default = col.get("default")
        default_str = default.strip() if isinstance(default, str) else ""
        out.append(ColumnSpec(name=name, path=str(path).strip(), default=default_str))
        seen.add(name)

    return out
