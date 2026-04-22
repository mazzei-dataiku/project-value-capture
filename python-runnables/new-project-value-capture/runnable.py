from __future__ import annotations

import dataiku
from dataiku.runnables import Runnable

from projectvaluecapture.admin_client import set_admin_client
from projectvaluecapture.new_project import create_project_with_fallback, ensure_hub_project


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

        project_name = (self.config or {}).get("projName")
        project_type = (self.config or {}).get("projType")

        if project_type == "POC" and project_name:
            self.project_name = f"POC {project_name}"
        else:
            self.project_name = project_name

        # Create the requested project (this is the core macro behavior).
        self.project_description = (self.config or {}).get("projectDescription", "")
        self.project_folder_id = (self.config or {}).get("projectFolderId")
        self.dss_login = (self.user_client.get_auth_info() or {}).get("authIdentifier")

        project_handle = create_project_with_fallback(self)

        # POC runs should not write to the audit log (intake is for tracking real work).
        if project_type == "POC":
            return {"projectKey": self.project_key, "status": "created", "logged": False}

        # TODO: implement audit log write
        return {"projectKey": self.project_key, "status": "created", "logged": False}
