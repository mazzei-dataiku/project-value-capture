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

    # Common wrapper key
    if "param1" in plugin_config and isinstance(plugin_config.get("param1"), dict):
        return plugin_config["param1"]

    # Pick the first dict-like value
    for value in plugin_config.values():
        if isinstance(value, dict):
            if "hub_project_name" in value or any(k.startswith("fc_") for k in value):
                return value

    # Sometimes settings get stringified as JSON
    for value in plugin_config.values():
        if isinstance(value, str) and value.strip().startswith("{"):
            try:
                import json

                parsed = json.loads(value)
                if isinstance(parsed, dict):
                    if "hub_project_name" in parsed or any(k.startswith("fc_") for k in parsed):
                        return parsed
            except Exception:
                pass

    # Wrapper dict: take first inner mapping as fallback
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
