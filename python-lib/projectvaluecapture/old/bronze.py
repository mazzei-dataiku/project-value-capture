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
        {"name": "plugin_version", "type": "string"},
        {"name": "intake_version", "type": "string"},
    ]


def ensure_managed_dataset(project, dataset_name: str, connection: str | None = None):
    existing = {d["name"] for d in project.list_datasets()}
    if dataset_name in existing:
        return project.get_dataset(dataset_name)

    builder = project.new_managed_dataset(dataset_name)

    if connection:
        builder.with_store_into(connection)
    else:
        # Best-effort fallback (requires hub variables to be set)
        builder.with_store_into(project.get_variables()["standard"]["default_connection"])

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
