from __future__ import annotations

import json
from pathlib import Path
from typing import Any


EXTRAS_PLUGIN_CONFIG_PATH = Path(
    "/home/dataiku/workspace/project-lib-versioned/python/project-value-capture.extras/"
    "runnable-configs/plugin_config.json"
)


class PluginConfigError(ValueError):
    pass


def unwrap_plugin_config(plugin_config: Any) -> dict[str, Any]:
    """Unwrap Dataiku plugin_config.

    Supports both shapes:
    - Flat dict: {"fc_proj_types": [...], ...}
    - Wrapped dict: {"param1": { ... }} (workaround used in this repo)
    """

    if not isinstance(plugin_config, dict) or not plugin_config:
        return {}

    if "hub_project_name" in plugin_config or any(k.startswith("fc_") for k in plugin_config):
        return plugin_config

    # Wrapper form: take first inner dict.
    if len(plugin_config) == 1:
        inner = next(iter(plugin_config.values()))
        if isinstance(inner, dict):
            return inner

    return plugin_config


def load_plugin_config_from_path(path: Path = EXTRAS_PLUGIN_CONFIG_PATH) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return unwrap_plugin_config(raw)


def get_required_list(cfg: dict[str, Any], key: str) -> list[str]:
    value = cfg.get(key)
    if not isinstance(value, list) or any(not isinstance(v, str) for v in value):
        raise PluginConfigError(f"Missing/invalid plugin config key: {key} (expected list[str])")
    return [v.strip() for v in value if isinstance(v, str) and v.strip()]


def get_list(cfg: dict[str, Any], key: str, default: list[str] | None = None) -> list[str]:
    try:
        return get_required_list(cfg, key)
    except PluginConfigError:
        return default or []
