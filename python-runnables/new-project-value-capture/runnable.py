from __future__ import annotations

import dataiku
from dataiku.runnables import Runnable

from projectvaluecapture.client_builder import create_admin_client, create_user_client
from projectvaluecapture.new_project import create_project_with_fallback, ensure_hub_project
from projectvaluecapture.bronze import append_row, ensure_managed_dataset
from projectvaluecapture.payload import INTAKE_VERSION, normalize_payload, to_json_str, utc_now_iso


class MyRunnable(Runnable):
    def __init__(self, project_key, config, plugin_config):
        self.config = config
        self.plugin_config = plugin_config

        # User client is always available; admin client is built in run() once
        # we have ensured plugin_config is fully populated.
        self.user_client = create_user_client()
        self.admin_client = None

    def get_progress_target(self):
        return None

    def run(self, progress_callback):
        # Hub settings are expected to be provided via plugin settings.
        # This runnable intentionally does not fetch/merge settings from presets.
        if isinstance(self.plugin_config, dict):
            self.plugin_config.setdefault("hub_project_name", "Project Value Hub")
            self.plugin_config.setdefault("hub_project_owner", "admin")
            self.plugin_config.setdefault(
                "hub_project_description", "Central hub for project intake logging"
            )

        # Build admin client only after plugin_config has been hydrated.
        # DSS does not always populate runnable plugin_config with PASSWORD fields,
        # so allow a fallback via the runnable config (set by the custom form).
        if self.admin_client is None:
            if isinstance(self.plugin_config, dict) and "admin_api_token" not in self.plugin_config:
                token_from_config = (self.config or {}).get("admin_api_token")
                if isinstance(token_from_config, str) and token_from_config.strip():
                    self.plugin_config["admin_api_token"] = token_from_config.strip()
            self.admin_client = create_admin_client(self.plugin_config)

        payload = normalize_payload(self.config or {})

        # Ensure the hub project exists (creates it if missing).
        hub_project = ensure_hub_project(self)

        project_name = payload.project_name
        project_type = payload.project_type

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

        plugin_cfg = getattr(self, "plugin_config", {}) or {}

        bronze_dataset_name = "projects_intake_bronze"
        if isinstance(plugin_cfg, dict) and isinstance(plugin_cfg.get("bronze_dataset_name"), str):
            bronze_dataset_name = plugin_cfg.get("bronze_dataset_name") or bronze_dataset_name

        bronze_dataset = ensure_managed_dataset(hub_project, dataset_name=bronze_dataset_name, connection=None)

        bronze_row = {
            "project_key": self.project_key,
            "project_name": payload.project_name,
            "created_at": utc_now_iso(),
            "created_by": self.dss_login or "",
            "project_type": payload.project_type,
            "gbu": payload.gbu,
            "apm_id": payload.apm_id or "",
            "business_owners_json": to_json_str(payload.business_owners),
            "technical_owners_json": to_json_str(payload.technical_owners),
            "problem_statement": payload.problem_statement,
            "solution_description": payload.solution_description,
            "links_json": to_json_str(payload.links),
            "value_drivers_json": to_json_str(payload.value_drivers),
            "intake_payload_json": to_json_str(payload.raw_payload),
            "plugin_version": "unknown",
            "intake_version": INTAKE_VERSION,
        }

        append_row(bronze_dataset, bronze_row)

        return {"projectKey": self.project_key, "status": "created", "logged": True}
