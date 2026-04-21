from __future__ import annotations

import re


def build_project_key(project_name: str, suffix: int | None = None, max_len: int = 24) -> str:
    base = re.sub(r"[^A-Z0-9]", "_", project_name.upper())[:max_len]
    if suffix is not None:
        return f"{base}_{suffix}"
    return base


def try_create_project(self):
    return self.admin_client.create_project(
        project_key=self.project_key,
        name=self.project_name,
        owner=self.dss_login,
        description=self.project_description,
        project_folder_id=self.project_folder_id,
    )


def create_project_with_fallback(self):
    # determine default folder if none specified
    if not self.project_folder_id:
        root_folder = self.user_client.get_root_project_folder()
        self.project_folder_id = root_folder.get_default_folder_for_project_creation().id

    # Loop over and try to create project
    max_attempts = 100

    for attempt in range(max_attempts):
        suffix = None if attempt == 0 else attempt
        self.project_key = build_project_key(self.project_name, suffix)

        try:
            project_handle = try_create_project(self)
            if project_handle:
                return project_handle

        except Exception as e:
            message = str(e).lower()
            if "already exists" in message:
                continue

            raise

    raise Exception(
        f"Unable to generate a unique project key after multiple {max_attempts} attempts"
    )


def _get_plugin_cfg(self) -> dict:
    cfg = getattr(self, "plugin_config", {}) or {}
    if isinstance(cfg, dict) and cfg:
        # Support wrapper format: {"param1": {...}}
        if "hub_project_name" not in cfg and len(cfg) == 1:
            inner = next(iter(cfg.values()))
            if isinstance(inner, dict):
                return inner
        return cfg
    return {}


def ensure_hub_project(self):
    """Ensure the hub project exists, creating it if missing.

    Reads fields from plugin_config (supports wrapper format {"param1": {...}}):
    - hub_project_name
    - hub_project_owner
    - hub_project_description (optional)
    - hub_project_folder_id (optional)
    """

    plugin_cfg = _get_plugin_cfg(self)

    hub_name = plugin_cfg.get("hub_project_name")
    if not hub_name:
        raise ValueError("Missing plugin_config.hub_project_name")

    hub_key = build_project_key(hub_name, max_len=64)

    try:
        return self.admin_client.get_project(hub_key)
    except Exception:
        pass

    self.project_name = hub_name
    self.project_description = plugin_cfg.get(
        "hub_project_description", "Central hub for project intake logging"
    )
    self.project_folder_id = plugin_cfg.get("hub_project_folder_id")
    self.project_key = hub_key
    self.dss_login = plugin_cfg.get("hub_project_owner", "admin")

    # Use fallback creation logic to avoid collisions.
    return create_project_with_fallback(self)
