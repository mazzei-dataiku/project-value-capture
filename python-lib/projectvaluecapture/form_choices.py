from __future__ import annotations

from typing import Any



def ensure_other_choice(values: list[str]) -> list[str]:
    seen = set()
    out: list[str] = []
    for v in values:
        if not isinstance(v, str):
            continue
        s = v.strip()
        if not s:
            continue
        if s not in seen:
            out.append(s)
            seen.add(s)
    if "Other" not in seen:
        out.append("Other")
    return out


def _unwrap_plugin_config(plugin_config: Any) -> dict[str, Any]:
    if not isinstance(plugin_config, dict) or not plugin_config:
        return {}

    # Flat dict
    if "hub_project_name" in plugin_config or any(k.startswith("fc_") for k in plugin_config):
        return plugin_config

    # Wrapper dict: take first inner mapping
    if len(plugin_config) == 1:
        inner = next(iter(plugin_config.values()))
        if isinstance(inner, dict):
            return inner

    return plugin_config


def _get_list(cfg: dict[str, Any], key: str) -> list[str]:
    value = cfg.get(key)
    if not isinstance(value, list):
        return []
    return [v.strip() for v in value if isinstance(v, str) and v.strip()]


def build_form_choices_response(plugin_config: Any) -> dict[str, Any]:
    cfg = _unwrap_plugin_config(plugin_config)

    return {
        "projTypes": _get_list(cfg, "fc_proj_types"),
        "GBUs": _get_list(cfg, "fc_gbus"),
        "businessUsers": ensure_other_choice(_get_list(cfg, "fc_business_users")),
        "technicalUsers": ensure_other_choice(_get_list(cfg, "fc_technical_users")),
        "valueDrivers": _get_list(cfg, "fc_value_drivers"),
        "nonFinImpactSize": _get_list(cfg, "fc_non_fin_impact_levels"),
        "financialValueDrivers": _get_list(cfg, "financial_value_drivers"),
    }
