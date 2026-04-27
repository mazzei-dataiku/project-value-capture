from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


INTAKE_VERSION = "v1"


@dataclass(frozen=True)
class NormalizedPayload:
    project_name: str
    project_type: str
    apm_id: str | None
    gbu: str
    business_owners: list[str]
    technical_owners: list[str]
    problem_statement: str
    solution_description: str
    links: list[dict[str, str]]
    value_drivers: list[dict[str, Any]]
    snowflake_enabled: bool
    snowflake_load_profile: bool
    snowflake_save_profile: bool
    snowflake_rows: list[dict[str, Any]]
    raw_payload: dict[str, Any]


def _require_non_empty_str(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Missing required field: {field}")
    return value.strip()


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _require_list_str(value: Any, field: str) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f"Missing required field: {field}")
    out: list[str] = []
    for item in value:
        if isinstance(item, str) and item.strip():
            out.append(item.strip())
    if not out:
        raise ValueError(f"Missing required field: {field}")
    return out


def _normalize_links(value: Any) -> list[dict[str, str]]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError("Invalid links payload (expected list)")

    out: list[dict[str, str]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        label = item.get("label")
        url = item.get("url")
        if not isinstance(label, str) or not label.strip():
            continue
        if not isinstance(url, str):
            url = ""
        out.append({"label": label.strip(), "url": url.strip()})
    return out


def _normalize_value_drivers(value: Any) -> list[dict[str, Any]]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError("Invalid value drivers payload (expected list)")

    out: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        driver = item.get("driver")
        if not isinstance(driver, str) or not driver.strip():
            continue
        impact = item.get("impact")
        out.append({"driver": driver.strip(), "impact": impact})
    return out


def _require_bool(value: Any, field: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        s = value.strip().lower()
        if s in {"1", "true", "yes", "y"}:
            return True
        if s in {"0", "false", "no", "n", ""}:
            return False
    if value is None:
        return False
    raise ValueError(f"Invalid boolean field: {field}")


def _normalize_snowflake_rows(value: Any) -> list[dict[str, Any]]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError("Invalid snowflakeRows payload (expected list)")

    out: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict):
            continue

        connection_name = item.get("connection_name")
        if not isinstance(connection_name, str) or not connection_name.strip():
            continue

        use = item.get("use")
        use_bool = use if isinstance(use, bool) else False

        def _cell(name: str) -> dict[str, Any]:
            cell = item.get(name)
            if isinstance(cell, dict):
                return cell
            return {}

        out.append(
            {
                "connection_name": connection_name.strip(),
                "use": use_bool,
                "warehouse": _cell("warehouse"),
                "database": _cell("database"),
                "role": _cell("role"),
                "schema": _cell("schema"),
            }
        )

    return out


def normalize_payload(config: dict[str, Any], plugin_config: dict[str, Any] | None = None) -> NormalizedPayload:
    # Required always
    project_name = _require_non_empty_str(config.get("projName"), "projName")
    project_type = _require_non_empty_str(config.get("projType"), "projType")

    # Snowflake vars (optional, validated below)
    snowflake_enabled = _require_bool(config.get("useSnowflakeVars"), "useSnowflakeVars")
    snowflake_rows = _normalize_snowflake_rows(config.get("snowflakeRows"))

    # Optional user-profile helpers for Snowflake vars
    snowflake_load_profile = _require_bool(
        config.get("loadSnowflakeFromProfile"), "loadSnowflakeFromProfile"
    )
    snowflake_save_profile = _require_bool(
        config.get("saveSnowflakeToProfile"), "saveSnowflakeToProfile"
    )

    # Required for certain project types
    apm_id = _optional_str(config.get("idAPM"))
    gbu = _optional_str(config.get("gbu"))

    business_owners = config.get("finalBusinessOwners")
    technical_owners = config.get("finalTechnicalOwners")

    problem_statement = _optional_str(config.get("problemStatement"))
    solution_description = _optional_str(config.get("solutionDescription"))

    links = _normalize_links(config.get("finalZippedLinks"))

    value_drivers = _normalize_value_drivers(config.get("finalZippedDrivers"))

    plugin_cfg = plugin_config or {}
    apm_enabled = bool(plugin_cfg.get("apm_id_enabled"))
    apm_types = plugin_cfg.get("apm_id_project_types")
    if not isinstance(apm_types, list):
        apm_types = []
    apm_types_norm = {
        str(t).strip().lower() for t in apm_types if isinstance(t, str) and t.strip()
    }
    needs_apm = apm_enabled and project_type.strip().lower() in apm_types_norm

    def _plugin_bool(key: str, default: bool = False) -> bool:
        v = plugin_cfg.get(key, default)
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            return v.strip().lower() in {"1", "true", "yes", "y"}
        if isinstance(v, int):
            return v != 0
        return default

    # Mirror existing rules in runnable.py / form: any non-POC requires full intake details.
    if project_type != "POC":
        if needs_apm and not apm_id:
            raise ValueError("You forgot to provide your APM ID. Please fix to proceed.")

        gbu_section_enabled = _plugin_bool("gbu_settings_enabled", _plugin_bool("fc_gbus_enabled", True))

        if gbu_section_enabled:
            if not gbu:
                raise ValueError("You forgot to select a GBU. Please fix to proceed.")
            business_owners_norm = _require_list_str(business_owners, "finalBusinessOwners")
            technical_owners_norm = _require_list_str(technical_owners, "finalTechnicalOwners")
        else:
            gbu = gbu or ""
            business_owners_norm = [s.strip() for s in business_owners or [] if isinstance(s, str) and s.strip()]
            technical_owners_norm = [s.strip() for s in technical_owners or [] if isinstance(s, str) and s.strip()]

        if not problem_statement:
            raise ValueError("You forgot to provide a Problem Statement. Please fix to proceed.")
        if not solution_description:
            raise ValueError("You forgot to provide a Solution Description. Please fix to proceed.")
        if not value_drivers:
            raise ValueError("You forgot to provide your project's Value Drivers. Please fix to proceed.")
    else:
        # For other types, normalize to empty lists.
        business_owners_norm = [s.strip() for s in business_owners or [] if isinstance(s, str) and s.strip()]
        technical_owners_norm = [s.strip() for s in technical_owners or [] if isinstance(s, str) and s.strip()]
        gbu = gbu or ""
        problem_statement = problem_statement or ""
        solution_description = solution_description or ""

    if snowflake_enabled:
        selected = [r for r in snowflake_rows if r.get("use") is True]
        for r in selected:
            cn = r.get("connection_name")
            for field in ["warehouse", "database", "role"]:
                cell = r.get(field) or {}
                editable = bool(cell.get("editable"))
                if not editable:
                    continue
                value = cell.get("value")
                if not isinstance(value, str) or not value.strip():
                    raise ValueError(
                        f"Snowflake {field} is required for connection {cn}. Please fix to proceed."
                    )

        # schema is optional even if editable

    return NormalizedPayload(
        project_name=project_name,
        project_type=project_type,
        apm_id=apm_id,
        gbu=gbu,
        business_owners=business_owners_norm,
        technical_owners=technical_owners_norm,
        problem_statement=problem_statement,
        solution_description=solution_description,
        links=links,
        value_drivers=value_drivers,
        snowflake_enabled=snowflake_enabled,
        snowflake_load_profile=snowflake_load_profile,
        snowflake_save_profile=snowflake_save_profile,
        snowflake_rows=snowflake_rows,
        raw_payload=config,
    )


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def to_json_str(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
