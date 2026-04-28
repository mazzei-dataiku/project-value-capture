from __future__ import annotations

from typing import Any


def _normalize_string_list(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []

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
    return out


def _unwrap_plugin_config(plugin_config: Any) -> dict[str, Any]:
    if not isinstance(plugin_config, dict) or not plugin_config:
        return {}

    # Flat dict
    if "hub_project_name" in plugin_config or any(k.startswith("fc_") for k in plugin_config):
        return plugin_config


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
    return _normalize_string_list(cfg.get(key))


def _get_str(cfg: dict[str, Any], key: str) -> str:
    value = cfg.get(key)
    if not isinstance(value, str):
        return ""
    return value.strip()


def _get_bool(cfg: dict[str, Any], key: str, default: bool = True) -> bool:
    value = cfg.get(key, default)
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y"}
    if isinstance(value, int):
        return value != 0
    return default


def _extract_gbu_settings(cfg: dict[str, Any]) -> tuple[list[str], dict[str, dict[str, list[str]]]]:
    """Return (gbu_names, mapping).

    mapping shape: {gbu_name: {"businessUsers": [...], "technicalUsers": [...]}}

    The UI is responsible for appending an "Other" option.
    """

    raw = cfg.get("gbu_settings")
    if not isinstance(raw, list):
        raw = []

    gbus: list[str] = []
    mapping: dict[str, dict[str, list[str]]] = {}

    for item in raw:
        if not isinstance(item, dict):
            continue

        gbu_name = item.get("gbu_name")
        if not isinstance(gbu_name, str) or not gbu_name.strip():
            continue
        gbu_name = gbu_name.strip()

        business = _normalize_string_list(item.get("business_owners"))
        technical = _normalize_string_list(item.get("technical_owners"))

        if gbu_name not in mapping:
            gbus.append(gbu_name)

        mapping[gbu_name] = {
            "businessUsers": business,
            "technicalUsers": technical,
        }

    # Backward compatibility fallback: old flat lists applied to every GBU.
    if not mapping:
        legacy_gbus = _get_list(cfg, "fc_gbus")
        legacy_business = _get_list(cfg, "fc_business_users")
        legacy_technical = _get_list(cfg, "fc_technical_users")
        for g in legacy_gbus:
            if g not in mapping:
                gbus.append(g)
            mapping[g] = {
                "businessUsers": legacy_business,
                "technicalUsers": legacy_technical,
            }

    return gbus, mapping


def build_form_choices_response(plugin_config: Any) -> dict[str, Any]:
    cfg = _unwrap_plugin_config(plugin_config)

    proj_types = _get_list(cfg, "fc_proj_types")
    if "POC" not in proj_types:
        proj_types.append("POC")

    gbu_enabled = _get_bool(cfg, "gbu_settings_enabled", True)
    gbus, gbu_settings_map = _extract_gbu_settings(cfg)

    return {
        "projTypes": proj_types,

        "support_wiki_page": _get_str(cfg, "support_wiki_page"),
        "support_admin_contact": _get_str(cfg, "support_admin_contact"),
        "support_user_community": _get_str(cfg, "support_user_community"),

        "enable_snowflake_vars": _get_bool(cfg, "enable_snowflake_vars", False),

        "apm_id_enabled": _get_bool(cfg, "apm_id_enabled", False),
        "apm_id_project_types": _get_list(cfg, "apm_id_project_types"),

        # Keep existing keys used by the UI.
        "fc_gbus_enabled": gbu_enabled,
        "GBUs": gbus,

        "fc_business_users_enabled": gbu_enabled,
        "fc_technical_users_enabled": gbu_enabled,

        # New mapping (used to filter owners by selected GBU).
        "gbu_settings_map": gbu_settings_map,

        "fc_value_drivers_enabled": _get_bool(cfg, "fc_value_drivers_enabled", True),
        "valueDrivers": _get_list(cfg, "fc_value_drivers"),

        "fc_non_fin_impact_levels_enabled": _get_bool(cfg, "fc_non_fin_impact_levels_enabled", True),
        "nonFinImpactSize": _get_list(cfg, "fc_non_fin_impact_levels"),

        "financial_value_drivers_enabled": _get_bool(cfg, "financial_value_drivers_enabled", True),
        "financialValueDrivers": _get_list(cfg, "financial_value_drivers"),
    }
