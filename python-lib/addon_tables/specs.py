from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
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


def _parse_simple_yaml_list_mapping(text: str) -> list[tuple[str, str]]:
    """Parse a minimal YAML list of 1-key mappings.

    Supports lines like:
    - warehouse: warehouse
    - {db: database}

    This intentionally avoids requiring PyYAML.
    """

    out: list[tuple[str, str]] = []
    for raw_line in (text or "").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if not line.startswith("-"):
            continue

        item = line[1:].strip()
        if item.startswith("{") and item.endswith("}"):
            item = item[1:-1].strip()

        if ":" not in item:
            continue

        left, right = item.split(":", 1)
        key = left.strip().strip("\"'")
        val = right.strip().strip("\"'")
        if not key or not val:
            continue

        out.append((key, val))

    return out


def load_params_mapping_yaml(provider: str) -> dict[str, str]:
    """Load provider mapping from `addon_tables/config/<provider>.yaml`.

    Returns mapping of output column name -> params key.
    """

    provider = (provider or "").strip().lower()
    if not provider:
        raise ValueError("Missing provider name for YAML mapping")

    config_path = Path(__file__).resolve().parent / "config" / f"{provider}.yaml"
    if not config_path.exists():
        raise ValueError(f"Missing YAML mapping file: {config_path}")

    text = config_path.read_text(encoding="utf-8")
    pairs = _parse_simple_yaml_list_mapping(text)

    mapping: dict[str, str] = {}
    for col, param in pairs:
        if col in mapping:
            continue
        mapping[col] = param

    if not mapping:
        raise ValueError(f"No mappings found in YAML file: {config_path}")

    return mapping


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
