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
    # Prefer DSS-provided plugin_config. In a deployed plugin, the workspace
    # extras path typically won't exist, so never fail hard if it's missing.
    effective_plugin_config = plugin_config or {}

    if not effective_plugin_config:
        try:
            if _EXTRAS_PLUGIN_CONFIG_PATH.exists():
                effective_plugin_config = _load_extras_plugin_config()
        except (OSError, ValueError, json.JSONDecodeError):
            effective_plugin_config = {}

    return build_form_choices_response(effective_plugin_config)
