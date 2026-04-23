from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


SNOWFLAKE_MAPPING_DATASET_DEFAULT = "snowflake_connnection_vars_map"


_VARIABLE_PATTERN = re.compile(r"^\$\{([A-Za-z_][A-Za-z0-9_]*)\}$")


@dataclass(frozen=True)
class SnowflakeMappingRow:
    connection_name: str
    warehouse: str
    database: str
    role: str
    schema: str


def is_variable_token(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    return _VARIABLE_PATTERN.match(value.strip()) is not None


def extract_variable_name(token: str) -> str:
    match = _VARIABLE_PATTERN.match((token or "").strip())
    if not match:
        raise ValueError(f"Invalid variable token (expected ${{VAR}}): {token!r}")
    return match.group(1)


def read_snowflake_mapping_rows(dataset) -> list[SnowflakeMappingRow]:
    """Read mapping rows from a DSSDataset.

    `dataikuapi.dss.dataset.DSSDataset.iter_rows()` yields lists of values. We map
    them to column names using the dataset schema, so that the call is executed
    with the same permissions as the DSSClient that owns `dataset`.

    Expected columns: connection_name, warehouse, database, role, schema.
    Missing columns are treated as empty strings.
    """

    schema = dataset.get_schema() or []
    columns: list[str] = []
    for c in schema:
        if isinstance(c, dict):
            name = c.get("name")
            if isinstance(name, str) and name.strip():
                columns.append(name.strip())

    rows: list[SnowflakeMappingRow] = []
    for values in dataset.iter_rows():
        if not isinstance(values, list):
            continue

        row = {columns[i]: values[i] for i in range(min(len(columns), len(values)))}

        connection_name = (row.get("connection_name") or "").strip()
        if not connection_name:
            continue

        rows.append(
            SnowflakeMappingRow(
                connection_name=connection_name,
                warehouse=str(row.get("warehouse") or "").strip(),
                database=str(row.get("database") or "").strip(),
                role=str(row.get("role") or "").strip(),
                schema=str(row.get("schema") or "").strip(),
            )
        )

    return rows


def mapping_rows_by_connection(mapping_rows: list[SnowflakeMappingRow]) -> dict[str, SnowflakeMappingRow]:
    out: dict[str, SnowflakeMappingRow] = {}
    for r in mapping_rows:
        out[r.connection_name] = r
    return out
