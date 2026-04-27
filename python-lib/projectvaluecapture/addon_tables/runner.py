from __future__ import annotations

import html
import json
from typing import Any

from projectvaluecapture.bronze import _infer_managed_connection

from .specs import ColumnSpec, get_by_path, parse_spec_json


DEFAULT_SNOWFLAKE_SPEC = {
    "columns": [
        {"name": "connection_name", "path": "name", "default": ""},
        {"name": "type", "path": "type", "default": ""},
    ]
}


def _unwrap_plugin_config(plugin_config: Any) -> dict[str, Any]:
    if not isinstance(plugin_config, dict) or not plugin_config:
        return {}

    if "admin_api_token" in plugin_config:
        return plugin_config

    if len(plugin_config) == 1:
        inner = next(iter(plugin_config.values()))
        if isinstance(inner, dict):
            return inner

    return plugin_config


def _get_str(cfg: dict[str, Any], key: str) -> str:
    v = cfg.get(key)
    return v.strip() if isinstance(v, str) else ""


def _get_bool(cfg: dict[str, Any], key: str, default: bool = False) -> bool:
    v = cfg.get(key, default)
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return v.strip().lower() in {"1", "true", "yes", "y"}
    if isinstance(v, int):
        return v != 0
    return default


def _schema_from_columns(columns: list[ColumnSpec]) -> list[dict[str, str]]:
    # Keep all values as strings for portability.
    return [{"name": c.name, "type": "string"} for c in columns]


def _render_html_result(title: str, details: dict[str, Any]) -> str:
    body = html.escape(json.dumps(details, indent=2, sort_keys=True))
    return f"<h3>{html.escape(title)}</h3><pre>{body}</pre>"


def build_snowflake_addon_dataset(
    *,
    admin_client,
    plugin_config: Any,
) -> dict[str, Any]:
    """Create/refresh the Snowflake add-on dataset in the hub project.

    Storage is a managed dataset, stored into the hub project's managed connection
    (same inference logic as the bronze intake dataset).

    The dataset schema/columns are driven by plugin settings `snowflake_addon_spec_json`.
    """

    cfg = _unwrap_plugin_config(plugin_config)

    if not _get_bool(cfg, "addon_tables_enabled", True):
        return {"status": "skipped", "reason": "addon_tables_enabled=false"}

    dataset_name = _get_str(cfg, "snowflake_addon_dataset_name")
    if not dataset_name:
        return {"status": "skipped", "reason": "snowflake_addon_dataset_name empty"}

    spec_json = _get_str(cfg, "snowflake_addon_spec_json")
    columns = parse_spec_json(spec_json)
    if not columns:
        # Fall back to default spec.
        columns = [ColumnSpec(**c) for c in DEFAULT_SNOWFLAKE_SPEC["columns"]]

    # Hub project
    from projectvaluecapture.new_project import build_project_key

    hub_name = _get_str(cfg, "hub_project_name") or "Project Value Hub"
    hub_key = build_project_key(hub_name, max_len=60)
    hub_project = admin_client.get_project(hub_key)

    # Gather rows
    connection_names = admin_client.list_connections_names("Snowflake") or []

    rows: list[dict[str, str]] = []
    errors: list[str] = []

    for name in connection_names:
        if not isinstance(name, str) or not name.strip():
            continue

        try:
            conn = admin_client.get_connection(name.strip())
            raw = conn.get_settings().get_raw() or {}
            # Include connection name at top-level for the spec.
            raw = {**raw, "name": name.strip()}
        except Exception as e:
            errors.append(f"Failed to read connection {name!r}: {e}")
            continue

        row: dict[str, str] = {}
        for col in columns:
            val = get_by_path(raw, col.path)
            if val is None:
                row[col.name] = col.default
            elif isinstance(val, (dict, list)):
                row[col.name] = json.dumps(val, sort_keys=True)
            else:
                row[col.name] = str(val)
        rows.append(row)

    # Recreate dataset to match schema exactly
    try:
        existing = {d.get("name") for d in (hub_project.list_datasets() or [])}
    except Exception:
        existing = set()

    if dataset_name in existing:
        try:
            hub_project.get_dataset(dataset_name).delete(drop_data=True)
        except Exception as e:
            raise RuntimeError(f"Unable to delete existing dataset {dataset_name!r}: {e}")

    builder = hub_project.new_managed_dataset(dataset_name)
    builder.with_store_into(_infer_managed_connection(hub_project))
    dataset = builder.create(overwrite=False)

    settings = dataset.get_settings()
    for col in _schema_from_columns(columns):
        settings.add_raw_schema_column(col)
    settings.save()

    core = dataset.get_as_core_dataset()
    try:
        import pandas as pd

        core.write_with_schema(pd.DataFrame(rows))
    except Exception as e:
        raise RuntimeError(f"Unable to write rows to dataset {dataset_name!r}: {e}")

    return {
        "status": "ok",
        "hub_project_key": hub_key,
        "dataset": dataset_name,
        "connection_count": len(connection_names),
        "row_count": len(rows),
        "errors": errors,
    }


def run_addon_tables_macro(*, admin_client, plugin_config: Any, build_snowflake: bool) -> str:
    results: dict[str, Any] = {"build_snowflake": build_snowflake}

    if build_snowflake:
        results["snowflake"] = build_snowflake_addon_dataset(admin_client=admin_client, plugin_config=plugin_config)

    return _render_html_result("Add-on Tables", results)
