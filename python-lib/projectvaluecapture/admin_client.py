from __future__ import annotations

import dataiku
from dataiku.runnables import utils


def set_admin_client(runnable) -> None:
    """Attach an admin client to the runnable instance.

    Uses `plugin_config["admin_api_token"]` when present, otherwise defaults to
    `creation1`. When executed outside the DSS macro runtime (missing shared
    secret), falls back to a regular `dataiku.api_client()`.
    """

    plugin_config = getattr(runnable, "plugin_config", {}) or {}

    admin_api_token = None
    if isinstance(plugin_config, dict):
        admin_api_token = plugin_config.get("admin_api_token")
        # Support the common wrapper format: {"param1": {...}}
        if not admin_api_token and len(plugin_config) == 1:
            inner = next(iter(plugin_config.values()))
            if isinstance(inner, dict):
                admin_api_token = inner.get("admin_api_token")

    if not isinstance(admin_api_token, str) or not admin_api_token.strip():
        admin_api_token = "creation1"

    user_client = dataiku.api_client()
    user_auth_info = user_client.get_auth_info()

    try:
        runnable.admin_client = utils.get_admin_dss_client(admin_api_token, user_auth_info)
        runnable.admin_client_is_admin = True
    except FileNotFoundError:
        runnable.admin_client = user_client
        runnable.admin_client_is_admin = False
