from __future__ import annotations

from typing import Any

from projectvaluecapture.config import get_list, unwrap_plugin_config


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


def build_form_choices_response(plugin_config: Any) -> dict[str, Any]:
    cfg = unwrap_plugin_config(plugin_config)

    return {
        "projTypes": get_list(cfg, "fc_proj_types"),
        "GBUs": get_list(cfg, "fc_gbus"),
        "businessUsers": ensure_other_choice(get_list(cfg, "fc_business_users")),
        "technicalUsers": ensure_other_choice(get_list(cfg, "fc_technical_users")),
        "valueDrivers": get_list(cfg, "fc_value_drivers"),
        "nonFinImpactSize": get_list(cfg, "fc_non_fin_impact_levels"),
        "financialValueDrivers": get_list(cfg, "financial_value_drivers"),
    }
