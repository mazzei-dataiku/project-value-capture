from __future__ import annotations

from typing import Any


def ensure_other_choice(values: list[str]) -> list[str]:
    """Ensure the special 'Other' choice exists exactly once."""

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


def as_choices_dict(form_choices: Any) -> dict[str, Any]:
    return {
        "projTypes": form_choices.proj_types,
        "GBUs": form_choices.gbus,
        "businessUsers": ensure_other_choice(form_choices.business_users),
        "technicalUsers": ensure_other_choice(form_choices.technical_users),
        "valueDrivers": form_choices.value_drivers,
        "nonFinImpactSize": form_choices.non_fin_impact_levels,
    }
