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


def _extract_admin_api_token_from_settings(raw: dict[str, Any]) -> str | None:
    if not isinstance(raw, dict):
        return None

    candidates: list[dict[str, Any]] = []

    if isinstance(raw.get("config"), dict):
        candidates.append(raw["config"])

    for preset in raw.get("presets", []) or []:
        pc = preset.get("pluginConfig")
        if isinstance(pc, dict):
            candidates.append(pc)

    for cfg in candidates:
        api_key = cfg.get("admin_api_token")
        if isinstance(api_key, str) and api_key.strip():
            return api_key.strip()

    return None


def _fetch_plugin_settings(with_secrets: bool) -> dict[str, Any] | None:
    """Fetch plugin settings via the raw API.

    The standard `plugin.get_settings().get_raw()` returns PASSWORD fields encrypted.
    In some DSS contexts, calling the endpoint with `withSecrets=true` returns
    decrypted values.
    """

    client = dataiku.api_client()
    if not hasattr(client, "_perform_json"):
        return None

    params = {"withSecrets": True} if with_secrets else None

    try:
        return client._perform_json("GET", f"/plugins/{_PLUGIN_ID}/settings", params=params)
    except Exception:
        return None


def _get_admin_api_key(plugin_config: Any) -> str:
    cfg = _unwrap_plugin_config(plugin_config)

    api_key = cfg.get("admin_api_token")
    if isinstance(api_key, str) and api_key.strip():
        api_key = api_key.strip()

        # If we already have a plain API key, use it.
        if not api_key.startswith("e:AES:"):
            return api_key

    # Try to fetch plugin settings. PASSWORD fields are stored encrypted, but STRING
    # fields would be returned in clear and can be used directly.
    for with_secrets in (True, False):
        raw = _fetch_plugin_settings(with_secrets=with_secrets)
        if not raw:
            continue

        token = _extract_admin_api_token_from_settings(raw)
        if not isinstance(token, str) or not token.strip():
            continue

        token = token.strip()
        if token.startswith("e:AES:"):
            raise ValueError(
                "admin_api_token is configured as a PASSWORD and is not available in clear text to the runnable. "
                "Either change `admin_api_token` to a STRING setting, or use a macro admin key profile "
                "(utils.get_admin_dss_client) instead of a raw API key."
            )

        return token

    raise ValueError(
        "Missing plugin config: admin_api_token. Configure an admin API key in plugin settings "
        "(or pass it via runnable pluginConfig)."
    )


def create_admin_client(plugin_config: Any) -> dataikuapi.DSSClient:
    api_key = _get_admin_api_key(plugin_config)
    return dataikuapi.DSSClient(build_dss_host(), api_key=api_key, no_check_certificate=True)


def create_user_client():
    return dataiku.api_client()
