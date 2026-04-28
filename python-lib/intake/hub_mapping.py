from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class HubMappingTable:
    connection_column: str
    columns: list[str]
    rows: list[dict[str, Any]]


def _normalize_schema_columns(schema_obj: Any) -> list[str]:
    if isinstance(schema_obj, dict):
        columns = schema_obj.get("columns")
    else:
        columns = schema_obj

    out: list[str] = []
    if isinstance(columns, list):
        for c in columns:
            if isinstance(c, dict):
                name = c.get("name")
            else:
                name = None
            if isinstance(name, str) and name.strip():
                out.append(name.strip())
    return out


def _pick_connection_column(columns: list[str]) -> str | None:
    normalized = {c.strip().lower(): c for c in columns if isinstance(c, str) and c.strip()}
    for candidate in ["connection_name", "connection", "name"]:
        if candidate in normalized:
            return normalized[candidate]
    return None


def read_hub_mapping_dataset(dataset) -> HubMappingTable:
    """Read a mapping dataset into rows with a dynamic schema.

    Expected to contain at least one identifier column among:
    - connection_name (preferred)
    - connection
    - name

    All other columns are treated as template fields.
    """

    schema_obj = dataset.get_schema() or {}
    columns = _normalize_schema_columns(schema_obj)
    if not columns:
        raise ValueError("Mapping dataset has no readable schema columns")

    connection_col = _pick_connection_column(columns)
    if connection_col is None:
        raise ValueError(
            "Mapping dataset is missing a connection identifier column. "
            "Expected one of: connection_name, connection, name"
        )

    template_cols = [c for c in columns if c != connection_col]

    rows: list[dict[str, Any]] = []
    for values in dataset.iter_rows():
        if not isinstance(values, list):
            continue
        row = {columns[i]: values[i] for i in range(min(len(columns), len(values)))}

        cn = row.get(connection_col)
        cn_str = str(cn or "").strip()
        if not cn_str:
            continue

        # Keep original column names, but normalize the connection identifier field.
        normalized_row: dict[str, Any] = {"connection_name": cn_str}
        for c in template_cols:
            normalized_row[c] = row.get(c)
        rows.append(normalized_row)

    return HubMappingTable(connection_column="connection_name", columns=template_cols, rows=rows)
