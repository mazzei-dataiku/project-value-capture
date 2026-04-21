from __future__ import annotations

from projectvaluecapture.config import load_plugin_config_from_path
from projectvaluecapture.form_choices import build_form_choices_response


def do(payload, confic, plugin_config, inputs):
    # Keep the form setup lightweight and config-driven.
    # Prefer DSS-provided plugin_config; fall back to workspace extras for local dev.
    effective_plugin_config = plugin_config
    if not effective_plugin_config:
        effective_plugin_config = load_plugin_config_from_path()

    return build_form_choices_response(effective_plugin_config)
