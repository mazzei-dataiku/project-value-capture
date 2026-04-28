from __future__ import annotations

import html

from helpers.client_builder import (
    create_admin_client,
    create_user_client,
    enforce_project_create_groups,
)
from addon_tables.runner import run_addon_tables_macro


from dataiku.runnables import Runnable


class MyRunnable(Runnable):
    def __init__(self, project_key, config, plugin_config):
        self.project_key = project_key
        self.config = config or {}
        self.plugin_config = plugin_config

        self.user_client = create_user_client()
        self.admin_client = None

    def get_progress_target(self):
        return None

    def run(self, progress_callback):
        # Restrict access to same group gate as project creation.
        enforce_project_create_groups(self.user_client, self.plugin_config)

        if self.admin_client is None:
            if isinstance(self.plugin_config, dict) and "admin_api_token" not in self.plugin_config:
                token_from_config = (self.config or {}).get("admin_api_token")
                if isinstance(token_from_config, str) and token_from_config.strip():
                    self.plugin_config["admin_api_token"] = token_from_config.strip()
            self.admin_client = create_admin_client(self.plugin_config)

        build_snowflake = bool((self.config or {}).get("build_snowflake", False))

        try:
            return run_addon_tables_macro(
                admin_client=self.admin_client,
                plugin_config=self.plugin_config,
                build_snowflake=build_snowflake,
            )
        except Exception as e:
            # Return HTML result with error (macro UI friendly)
            return f"<h3>Add-on Tables</h3><div class='alert alert-danger'>{html.escape(str(e))}</div>"
