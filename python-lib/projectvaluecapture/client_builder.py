from __future__ import annotations

import os
from typing import Any

import dataiku
import dataikuapi

_PLUGIN_ID = "project-value-capture"


def _unwrap_plugin_config(plugin_config: Any) -> dict[str, Any]:
    if not isinstance(plugin_config, dict) or not plugin_config:
        return {}

    if "admin_api_token" in plugin_config:
        return plugin_config

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


def _get_admin_api_key(plugin_config: Any) -> str:
    cfg = _unwrap_plugin_config(plugin_config)

    api_key = cfg.get("admin_api_token")
    if isinstance(api_key, str) and api_key.strip():
        api_key = api_key.strip()

        # DSS stores PASSWORD values encrypted; require a plain API key here.
        if api_key.startswith("e:AES:"):
            raise ValueError(
                "admin_api_token is encrypted (e:AES:...). "
                "The runnable requires the cleartext key in plugin settings."
            )

        return api_key

    raise ValueError(
        "Missing plugin config: admin_api_token. Configure an admin API key in plugin settings."
    )


def create_admin_client(plugin_config: Any) -> dataikuapi.DSSClient:
    api_key = _get_admin_api_key(plugin_config)
    return dataikuapi.DSSClient(build_dss_host(), api_key=api_key, no_check_certificate=True)


def create_user_client():
    return dataiku.api_client()
