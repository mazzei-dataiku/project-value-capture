from __future__ import annotations

import re


def build_project_key(project_name: str, suffix: int | None = None, max_len: int = 60) -> str:
    # Keep a conservative base length so we can append "_999" while staying under ~64 chars.
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


def create_project_with_fallback(self, key_max_len: int = 60):
    # determine default folder if none specified
    if not self.project_folder_id:
        root_folder = self.user_client.get_root_project_folder()
        self.project_folder_id = root_folder.get_default_folder_for_project_creation().id

    # Loop over and try to create project.
    # Attempt 0 uses the base key, then _1 ... _999.
    max_attempts = 1000

    for attempt in range(max_attempts):
        suffix = None if attempt == 0 else attempt
        if suffix is not None and suffix > 999:
            break
        self.project_key = build_project_key(self.project_name, suffix, max_len=key_max_len)

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


def _unwrap_plugin_config(plugin_config) -> dict:
    if not isinstance(plugin_config, dict) or not plugin_config:
        return {}

    if "hub_project_name" in plugin_config:
        return plugin_config

    # Common wrapper key
    if "param1" in plugin_config and isinstance(plugin_config.get("param1"), dict):
        return plugin_config["param1"]

    # Wrapper dict: take first inner mapping
    if len(plugin_config) == 1:
        inner = next(iter(plugin_config.values()))
        if isinstance(inner, dict):
            return inner

    return plugin_config


def _load_dss_plugin_settings_config(plugin_id: str) -> dict:
    """Best-effort read of plugin settings from DSS.

    In some DSS runtimes, the `plugin_config` passed to the runnable may be
    missing keys (especially when settings are stored in a parameter set preset).
    """

    try:
        import dataiku

        client = dataiku.api_client()
        plugin = client.get_plugin(plugin_id)
        raw = plugin.get_settings().get_raw()

        candidates = []
        if isinstance(raw.get("config"), dict):
            candidates.append(raw["config"])
        for preset in raw.get("presets", []) or []:
            pc = preset.get("pluginConfig")
            if isinstance(pc, dict):
                candidates.append(pc)

        for cfg in candidates:
            if "hub_project_name" in cfg:
                return cfg

        return {}
    except Exception:
        return {}


def _get_plugin_cfg(self) -> dict:
    # 1) use runnable-provided plugin_config
    cfg = _unwrap_plugin_config(getattr(self, "plugin_config", {}) or {})
    if cfg.get("hub_project_name"):
        return cfg

    # 2) fall back to DSS plugin settings (parameter sets are often stored there)
    cfg2 = _load_dss_plugin_settings_config("project-value-capture")
    if cfg2.get("hub_project_name"):
        return cfg2

    return cfg


def ensure_hub_project(self):
    """Ensure the hub project exists, creating it if missing.

    Reads fields from plugin_config (supports wrapper format {"param1": {...}}):
    - hub_project_name
    - hub_project_owner
    - hub_project_description (optional)
    """

    plugin_cfg = _get_plugin_cfg(self)

    hub_name = plugin_cfg.get("hub_project_name")
    if not hub_name:
        raise ValueError("Missing plugin_config.hub_project_name")

    hub_key = build_project_key(hub_name, max_len=64)

    # A get_project() failure isn't always "not found" (could be permissions, networking,
    # invalid key, etc.). Try to detect "missing" by listing projects.
    try:
        project = self.admin_client.get_project(hub_key)
        # Force an API call to validate permissions early (otherwise failures show up later
        # when accessing datasets/objects in the hub project).
        project.get_permissions()
        return project
    except Exception:
        pass

    try:
        existing_keys = {p.get("projectKey") for p in (self.admin_client.list_projects() or [])}
        if hub_key in existing_keys:
            project = self.admin_client.get_project(hub_key)
            project.get_permissions()
            return project
    except Exception:
        # If we can't list projects, fall through to a create attempt.
        pass

    self.project_name = hub_name
    self.project_description = plugin_cfg.get(
        "hub_project_description", "Central hub for project intake logging"
    )
    self.project_folder_id = None
    self.project_key = hub_key
    self.dss_login = plugin_cfg.get("hub_project_owner", "admin")

    # Use fallback creation logic to avoid collisions.
    # Hub projects allow longer keys; they are derived from hub_project_name.
    return create_project_with_fallback(self, key_max_len=64)
