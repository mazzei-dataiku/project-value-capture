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


def _fallback_zip_value_drivers(config: dict[str, Any]) -> list[dict[str, Any]] | None:
    drivers = config.get("drivers")
    impacts = config.get("impacts")

    if not isinstance(drivers, list):
        return None
    if not isinstance(impacts, list):
        impacts = []

    out: list[dict[str, Any]] = []
    for idx in range(max(len(drivers), len(impacts))):
        driver_item = drivers[idx] if idx < len(drivers) else None
        impact_item = impacts[idx] if idx < len(impacts) else None

        driver_value = None
        if isinstance(driver_item, dict):
            driver_value = driver_item.get("driver")
        elif isinstance(driver_item, str):
            driver_value = driver_item

        impact_value: Any = None
        if isinstance(impact_item, dict):
            impact_value = impact_item.get("impact")
        else:
            impact_value = impact_item

        if isinstance(driver_value, str) and driver_value.strip():
            out.append({"driver": driver_value.strip(), "impact": impact_value})

    return out


def normalize_payload(config: dict[str, Any]) -> NormalizedPayload:
    # Required always
    project_name = _require_non_empty_str(config.get("projName"), "projName")
    project_type = _require_non_empty_str(config.get("projType"), "projType")

    # Required for certain project types
    apm_id = _optional_str(config.get("idAPM"))
    gbu = _optional_str(config.get("gbu"))

    business_owners = config.get("finalBusinessOwners")
    technical_owners = config.get("finalTechnicalOwners")

    problem_statement = _optional_str(config.get("problemStatement"))
    solution_description = _optional_str(config.get("solutionDescription"))

    links = _normalize_links(config.get("finalZippedLinks"))

    value_drivers = _normalize_value_drivers(config.get("finalZippedDrivers"))
    if not value_drivers:
        fallback = _fallback_zip_value_drivers(config)
        if fallback:
            value_drivers = fallback

    # Mirror existing rules in runnable.py
    if project_type in ["Ad-Hoc", "Industrialization"]:
        if project_type == "Industrialization" and not apm_id:
            raise ValueError("You forgot to provide your APM ID. Please fix to proceed.")
        if not gbu:
            raise ValueError("You forgot to select a GBU. Please fix to proceed.")
        business_owners_norm = _require_list_str(business_owners, "finalBusinessOwners")
        technical_owners_norm = _require_list_str(technical_owners, "finalTechnicalOwners")
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
        raw_payload=config,
    )


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def to_json_str(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
