from __future__ import annotations

import json
from pathlib import Path

from projectvaluecapture.form_choices import build_form_choices_response


_EXTRAS_PLUGIN_CONFIG_PATH = Path(
    "/home/dataiku/workspace/project-lib-versioned/python/project-value-capture.extras/"
    "runnable-configs/plugin_config.json"
)


def _load_extras_plugin_config() -> dict:
    return json.loads(_EXTRAS_PLUGIN_CONFIG_PATH.read_text(encoding="utf-8"))


def do(payload, confic, plugin_config, inputs):
    # Keep the form setup lightweight and config-driven.
    # Prefer DSS-provided plugin_config. In some DSS contexts the plugin config
    # may be empty; fall back to the workspace extras file for testing.
    effective_plugin_config = plugin_config or {}

    choices = build_form_choices_response(effective_plugin_config)

    # If the resolved plugin_config didn't include fc_* values,
    # fall back to extras (local dev/testing environment).
    if not choices.get("projTypes"):
        try:
            if _EXTRAS_PLUGIN_CONFIG_PATH.exists():
                choices = build_form_choices_response(_load_extras_plugin_config())
        except (OSError, ValueError, json.JSONDecodeError):
            pass

    return choices
