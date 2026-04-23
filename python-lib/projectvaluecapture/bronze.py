from __future__ import annotations

from typing import Any


def get_plugin_version() -> str:
    # Avoid importing json/parsing plugin.json from disk in the runnable
    # unless needed. This keeps failure modes small.
    return "unknown"


def bronze_schema_columns() -> list[dict[str, str]]:
    # Keep types to basic scalar types for portability.
    return [
        {"name": "project_key", "type": "string"},
        {"name": "project_name", "type": "string"},
        {"name": "created_at", "type": "string"},
        {"name": "created_by", "type": "string"},
        {"name": "project_type", "type": "string"},
        {"name": "gbu", "type": "string"},
        {"name": "apm_id", "type": "string"},
        {"name": "business_owners_json", "type": "string"},
        {"name": "technical_owners_json", "type": "string"},
        {"name": "problem_statement", "type": "string"},
        {"name": "solution_description", "type": "string"},
        {"name": "links_json", "type": "string"},
        {"name": "value_drivers_json", "type": "string"},
        {"name": "intake_payload_json", "type": "string"},
        {"name": "intake_version", "type": "string"},
    ]


def _infer_managed_connection(project) -> str | None:
    """Infer a connection for managed dataset creation.

    DSS requires an explicit connection for managed dataset creation in many setups.
    We try to infer it from project variables or existing datasets.
    """

    # 1) Hub project variables
    try:
        variables = project.get_variables() or {}
        standard = variables.get("standard") or {}
        default_connection = standard.get("default_connection")
        if isinstance(default_connection, str) and default_connection.strip():
            return default_connection.strip()
    except Exception:
        pass

    # 2) Reuse the connection of an existing dataset in the hub project
    try:
        for dataset in project.list_datasets() or []:
            name = dataset.get("name")
            if not isinstance(name, str) or not name.strip():
                continue
            try:
                settings = project.get_dataset(name).get_settings().get_raw() or {}
                params = settings.get("params") or {}
                conn = params.get("connection")
                if isinstance(conn, str) and conn.strip():
                    return conn.strip()
            except Exception:
                continue
    except Exception:
        pass

    # 3) Common default connection name
    return "filesystem_managed"


def _existing_schema_column_names(dataset) -> set[str]:
    """Return existing column names for a dataset.

    This uses the dataset settings raw schema, which may differ slightly by DSS version.
    """

    try:
        raw = dataset.get_settings().get_raw() or {}
    except Exception:
        return set()

    schema = raw.get("schema")
    if isinstance(schema, dict):
        columns = schema.get("columns")
    else:
        columns = schema

    if not isinstance(columns, list):
        return set()

    out: set[str] = set()
    for col in columns:
        if isinstance(col, dict):
            name = col.get("name")
            if isinstance(name, str) and name.strip():
                out.add(name.strip())
    return out


def _ensure_bronze_schema(dataset) -> None:
    existing_cols = _existing_schema_column_names(dataset)
    if not existing_cols:
        # If we can't read schema, avoid potentially destructive writes.
        return

    settings = dataset.get_settings()
    to_add = [c for c in bronze_schema_columns() if c.get("name") not in existing_cols]
    if not to_add:
        return

    for col in to_add:
        settings.add_raw_schema_column(col)

    settings.save()


def ensure_managed_dataset(project, dataset_name: str, connection: str | None = None):
    try:
        existing = {d["name"] for d in project.list_datasets()}
    except Exception as e:
        raise RuntimeError(
            "Unable to list datasets in the hub project. "
            "The macro admin key/user likely lacks permissions on the hub project. "
            f"Underlying error: {e}"
        )

    if dataset_name in existing:
        dataset = project.get_dataset(dataset_name)
        _ensure_bronze_schema(dataset)
        return dataset

    builder = project.new_managed_dataset(dataset_name)

    resolved_connection = connection or _infer_managed_connection(project)
    if isinstance(resolved_connection, str) and resolved_connection.strip():
        builder.with_store_into(resolved_connection.strip())
    else:
        raise ValueError(
            "Unable to infer a managed connection for the hub dataset. "
            "Set the hub project's variable standard.default_connection, "
            "or configure a connection name in plugin settings."
        )

    dataset = builder.create(overwrite=False)
    settings = dataset.get_settings()

    for col in bronze_schema_columns():
        settings.add_raw_schema_column(col)

    settings.save()
    return dataset


def append_row(dataset, row: dict[str, Any]) -> None:
    import pandas as pd

    core = dataset.get_as_core_dataset()
    core.spec_item["appendMode"] = True
    core.write_with_schema(pd.DataFrame([row]))
