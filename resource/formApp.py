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
    # Prefer DSS-provided plugin_config; fall back to workspace extras for local dev.
    effective_plugin_config = plugin_config
    if not effective_plugin_config:
        effective_plugin_config = _load_extras_plugin_config()

    return build_form_choices_response(effective_plugin_config)
