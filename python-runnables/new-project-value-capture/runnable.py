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

        self.admin_client = create_admin_client(plugin_config)
        self.user_client = create_user_client()

    def get_progress_target(self):
        return None

    def run(self, progress_callback):
        # Ensure hub settings exist in plugin_config.
        # In some DSS runtimes, runnable plugin_config can be empty even when the
        # plugin settings are filled (values end up in presets/parameter sets).
        if isinstance(self.plugin_config, dict):
            target_cfg = self.plugin_config
            if "param1" in self.plugin_config and isinstance(self.plugin_config.get("param1"), dict):
                target_cfg = self.plugin_config["param1"]

            if not target_cfg.get("hub_project_name"):
                try:
                    plugin = self.user_client.get_plugin("project-value-capture")
                    raw = plugin.get_settings().get_raw()
                    for preset in raw.get("presets", []) or []:
                        pc = preset.get("pluginConfig")
                        if isinstance(pc, dict) and pc.get("hub_project_name"):
                            target_cfg.update(pc)
                            break
                except Exception:
                    pass

            target_cfg.setdefault("hub_project_name", "Project Value Hub")
            target_cfg.setdefault("hub_project_owner", "admin")
            target_cfg.setdefault(
                "hub_project_description", "Central hub for project intake logging"
            )

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
        if isinstance(plugin_cfg, dict) and "param1" in plugin_cfg and isinstance(plugin_cfg.get("param1"), dict):
            plugin_cfg = plugin_cfg["param1"]

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
