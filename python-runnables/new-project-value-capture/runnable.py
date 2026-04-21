from __future__ import annotations

import dataiku
from dataiku.runnables import Runnable

from projectvaluecapture.admin_client import set_admin_client
from projectvaluecapture.new_project import ensure_hub_project


class MyRunnable(Runnable):
    def __init__(self, project_key, config, plugin_config):
        self.config = config
        self.plugin_config = plugin_config

        set_admin_client(self)

    def get_progress_target(self):
        return None

    def run(self, progress_callback):
        # Attach DSS clients used by helper modules.
        self.user_client = dataiku.api_client()

        # Ensure the hub project exists (creates it if missing).
        ensure_hub_project(self)

        return Exception("Not implemented")
