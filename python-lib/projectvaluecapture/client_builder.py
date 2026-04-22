from __future__ import annotations

import os
from typing import Any

import dataiku
import dataikuapi


def _unwrap_plugin_config(plugin_config: Any) -> dict[str, Any]:
    if not isinstance(plugin_config, dict) or not plugin_config:
        return {}

    if "admin_api_token" in plugin_config:
        return plugin_config

    if "param1" in plugin_config and isinstance(plugin_config.get("param1"), dict):
        return plugin_config["param1"]

    if len(plugin_config) == 1:
        inner = next(iter(plugin_config.values()))
        if isinstance(inner, dict):
            return inner

    return plugin_config


def build_dss_host() -> str:
    """Build a DSS base URL suitable for API calls.

    In macro runtime, the backend public API is reachable on localhost at DKU_BACKEND_PORT.
    """

    protocol = os.environ.get("DKU_BACKEND_PROTOCOL", "http")
    port = os.environ.get("DKU_BACKEND_PORT", "10001")

    # Use localhost when possible (works inside macro runtime and avoids cert issues)
    host = "127.0.0.1"

    return f"{protocol}://{host}:{port}"


def create_admin_client(plugin_config: Any) -> dataikuapi.DSSClient:
    cfg = _unwrap_plugin_config(plugin_config)

    api_key = cfg.get("admin_api_token")
    if not isinstance(api_key, str) or not api_key.strip():
        raise ValueError("Missing plugin config: admin_api_token")

    return dataikuapi.DSSClient(build_dss_host(), api_key=api_key.strip(), no_check_certificate=True)


def create_user_client():
    return dataiku.api_client()
