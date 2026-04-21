from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


EXTRAS_PLUGIN_CONFIG_PATH = Path(
    "/home/dataiku/workspace/project-lib-versioned/python/project-value-capture.extras/"
    "runnable-configs/plugin_config.json"
)


class PluginConfigError(ValueError):
    pass


@dataclass(frozen=True)
class FormChoices:
    proj_types: list[str]
    gbus: list[str]
    business_users: list[str]
    technical_users: list[str]
    value_drivers: list[str]
    non_fin_impact_levels: list[str]


@dataclass(frozen=True)
class PluginConfig:
    admin_client_profile: str
    hub_project_name: str
    hub_project_owner: str
    bronze_dataset_name: str
    form_choices: FormChoices
    financial_value_drivers: list[str]


def _first_mapping_value(data: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(data, dict) or not data:
        raise PluginConfigError(
            "plugin_config.json must be a non-empty object like {\"param1\": {...}}"
        )

    first = next(iter(data.values()))
    if not isinstance(first, dict):
        raise PluginConfigError(
            "plugin_config.json must contain an object value like {\"param1\": {...}}"
        )
    return first


def _require_str(cfg: dict[str, Any], key: str) -> str:
    value = cfg.get(key)
    if not isinstance(value, str) or not value.strip():
        raise PluginConfigError(f"Missing/invalid plugin config key: {key}")
    return value.strip()


def _require_list_str(cfg: dict[str, Any], key: str) -> list[str]:
    value = cfg.get(key)
    if not isinstance(value, list) or any(not isinstance(v, str) for v in value):
        raise PluginConfigError(f"Missing/invalid plugin config key: {key} (expected list[str])")
    return [v for v in (s.strip() for s in value) if v]


def load_plugin_config_from_path(path: Path = EXTRAS_PLUGIN_CONFIG_PATH) -> PluginConfig:
    raw = json.loads(path.read_text(encoding="utf-8"))
    cfg = _first_mapping_value(raw)

    admin_client_profile = _require_str(cfg, "admin_client_profile")
    hub_project_name = _require_str(cfg, "hub_project_name")
    hub_project_owner = _require_str(cfg, "hub_project_owner")
    bronze_dataset_name = _require_str(cfg, "bronze_dataset_name")

    # Form choices are stored as top-level lists in plugin_config.json
    form_choices = FormChoices(
        proj_types=_require_list_str(cfg, "fc_proj_types"),
        gbus=_require_list_str(cfg, "fc_gbus"),
        business_users=_require_list_str(cfg, "fc_business_users"),
        technical_users=_require_list_str(cfg, "fc_technical_users"),
        value_drivers=_require_list_str(cfg, "fc_value_drivers"),
        non_fin_impact_levels=_require_list_str(cfg, "fc_non_fin_impact_levels"),
    )

    financial_value_drivers = _require_list_str(cfg, "financial_value_drivers")

    return PluginConfig(
        admin_client_profile=admin_client_profile,
        hub_project_name=hub_project_name,
        hub_project_owner=hub_project_owner,
        bronze_dataset_name=bronze_dataset_name,
        form_choices=form_choices,
        financial_value_drivers=financial_value_drivers,
    )
