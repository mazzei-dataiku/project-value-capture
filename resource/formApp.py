from __future__ import annotations

import json
from pathlib import Path

import dataiku

from projectvaluecapture.form_choices import build_form_choices_response


_PLUGIN_ID = "project-value-capture"

_EXTRAS_PLUGIN_CONFIG_PATH = Path(
    "/home/dataiku/workspace/project-lib-versioned/python/project-value-capture.extras/"
    "runnable-configs/plugin_config.json"
)


def _load_extras_plugin_config() -> dict:
    return json.loads(_EXTRAS_PLUGIN_CONFIG_PATH.read_text(encoding="utf-8"))


def _load_dss_plugin_settings_config() -> dict:
    """Load plugin settings from DSS.

    In some DSS contexts, the `plugin_config` argument passed to custom UI Python
    can be empty. This function fetches resolved settings from DSS and returns
    the first config block that contains `fc_*` keys.
    """

    client = dataiku.api_client()
    plugin = client.get_plugin(_PLUGIN_ID)
    raw = plugin.get_settings().get_raw()

    candidates = []

    # 1) global plugin settings
    if isinstance(raw.get("config"), dict):
        candidates.append(raw["config"])

    # 2) preset pluginConfig blocks (often where parameter set values land)
    for preset in raw.get("presets", []) or []:
        pc = preset.get("pluginConfig")
        if isinstance(pc, dict):
            candidates.append(pc)

    for cfg in candidates:
        if any(k.startswith("fc_") for k in cfg.keys()) or "financial_value_drivers" in cfg:
            return cfg

    return {}


def do(payload, confic, plugin_config, inputs):
    # Keep the form setup lightweight and config-driven.
    # Preferred precedence:
    # 1) UI-provided plugin_config (when populated)
    # 2) DSS plugin settings (resolved)
    # 3) workspace extras file (local dev)

    effective_plugin_config = plugin_config or {}
    choices = build_form_choices_response(effective_plugin_config)

    if not choices.get("projTypes"):
        try:
            choices = build_form_choices_response(_load_dss_plugin_settings_config())
        except Exception:
            pass

    if not choices.get("projTypes"):
        try:
            if _EXTRAS_PLUGIN_CONFIG_PATH.exists():
                choices = build_form_choices_response(_load_extras_plugin_config())
        except (OSError, ValueError, json.JSONDecodeError):
            pass

    if not choices.get("projTypes"):
        raise Exception(
            "Plugin settings are missing form choice lists. "
            "Configure plugin settings with keys like fc_proj_types, fc_gbus, fc_business_users, "
            "fc_technical_users, fc_value_drivers, fc_non_fin_impact_levels."
        )

    return choices
