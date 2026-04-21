from __future__ import annotations

import dataiku
from dataiku.runnables import Runnable
from dataiku.runnables import utils



class MyRunnable(Runnable):
    """DSS runnable: create project intake + bronze audit log."""

    def __init__(self, project_key, config, plugin_config):
        self.config = config
        self.plugin_config = plugin_config

    def get_progress_target(self):
        return None

    def run(self, progress_callback):
        user_client = dataiku.api_client()
        user_auth_info = user_client.get_auth_info()

        cfg = load_plugin_config_from_path()

        # Admin macro execution client
        # In a real DSS macro run, utils.get_admin_dss_client works.
        # In local Code Studio execution, DIP_HOME/shared-secret isn't present.
        # Fall back to regular api_client for local smoke tests.
        try:
            admin_client = utils.get_admin_dss_client(cfg.admin_client_profile, user_auth_info)
        except FileNotFoundError:
            admin_client = user_client

        payload = normalize_payload(self.config)

        # Create the new project (as admin, owned by the requester)
        base_key = to_dss_project_key(payload.project_name)
        new_project_key = utils.make_unique_project_key(admin_client, base_key)

        project = admin_client.create_project(
            project_key=new_project_key,
            name=new_project_key,
            owner=user_auth_info["authIdentifier"],
        )

        # Only after successful creation: ensure hub + bronze log.
        hub_project = ensure_hub_project(
            admin_client,
            hub_project_name=cfg.hub_project_name,
            hub_project_owner=cfg.hub_project_owner,
        )

        bronze_dataset = ensure_managed_dataset(
            hub_project,
            dataset_name=cfg.bronze_dataset_name,
            connection=None,
        )

        bronze_row = {
            "project_key": new_project_key,
            "project_name": payload.project_name,
            "created_at": utc_now_iso(),
            "created_by": user_auth_info["authIdentifier"],
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

        # Optional: add checklist link for industrialization.
        if payload.project_type == "Industrialization":
            metadata = project.get_metadata()
            metadata.setdefault("checklists", {}).setdefault("checklists", [])
            metadata["checklists"]["checklists"].append(
                {
                    "title": "Project Documentation",
                    "items": [
                        {
                            "text": "Update project value capture entry in [WebApp](web_app:PROJECTVALUEHUB.NGogdna)"
                        }
                    ],
                }
            )
            project.set_metadata(metadata)

        return json.dumps({"projectKey": new_project_key})
