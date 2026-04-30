from __future__ import annotations

from uuid import uuid4

import dataiku
from dataiku.runnables import Runnable

from helpers.client_builder import (
    create_admin_client,
    create_user_client,
    enforce_project_create_groups,
)
from intake.new_project import create_project_with_fallback, ensure_hub_project
from intake.bronze import append_status, ensure_managed_dataset
from intake.payload import INTAKE_VERSION, normalize_payload, to_json_str, utc_now_iso
from intake.snowflake_vars import extract_variable_name, is_variable_token


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

        # Enforce group access before using the admin client.
        requesting_login, requesting_groups = enforce_project_create_groups(
            self.user_client, self.plugin_config
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

        payload = normalize_payload(
            self.config or {},
            plugin_config=self.plugin_config if isinstance(self.plugin_config, dict) else None,
        )

        plugin_cfg = getattr(self, "plugin_config", {}) or {}
        if isinstance(plugin_cfg, dict) and "enable_custom_hook" not in plugin_cfg and len(plugin_cfg) == 1:
            inner = next(iter(plugin_cfg.values()))
            if isinstance(inner, dict):
                plugin_cfg = inner

        bronze_dataset = None
        bronze_row_base = None
        intake_run_id = None

        project_name = payload.project_name
        project_type = payload.project_type

        # POC projects are intentionally not logged.
        if project_type != "POC":
            # Ensure the hub project exists (creates it if missing).
            hub_project = ensure_hub_project(self)

            bronze_dataset_name = "projects_intake_bronze"
            if isinstance(plugin_cfg, dict) and isinstance(plugin_cfg.get("bronze_dataset_name"), str):
                bronze_dataset_name = plugin_cfg.get("bronze_dataset_name") or bronze_dataset_name

            bronze_dataset = ensure_managed_dataset(
                hub_project, dataset_name=bronze_dataset_name, connection=None
            )

            intake_run_id = str(uuid4())

            bronze_row_base = {
                "project_key": "",
                "project_name": payload.project_name,
                "created_at": utc_now_iso(),
                "created_by": requesting_login or "",
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
                "intake_version": INTAKE_VERSION,
            }

            append_status(
                bronze_dataset,
                intake_run_id=intake_run_id,
                intake_status="STARTED",
                base_row=bronze_row_base,
            )


        if project_type == "POC" and project_name:
            self.project_name = f"POC {project_name}"
        else:
            self.project_name = project_name

        # Create the requested project (this is the core macro behavior).
        self.project_description = (self.config or {}).get("projectDescription", "")
        self.project_folder_id = (self.config or {}).get("projectFolderId")
        self.dss_login = requesting_login
        self.dss_groups = requesting_groups

        project_handle = create_project_with_fallback(self)

        if payload.snowflake_save_profile and payload.snowflake_enabled:
            try:
                own_settings = self.user_client.get_own_user().get_settings()
                props = own_settings.user_properties

                for row in payload.snowflake_rows:
                    if not isinstance(row, dict) or not row.get("use"):
                        continue

                    cells = row.get("cells")
                    if not isinstance(cells, dict):
                        continue

                    for cell in cells.values():
                        if not isinstance(cell, dict) or not cell.get("editable"):
                            continue

                        template = cell.get("template")
                        if not is_variable_token(template):
                            continue

                        value = cell.get("value")
                        if not isinstance(value, str):
                            continue
                        value = value.strip()
                        if not value:
                            continue

                        var_name = extract_variable_name(str(template))
                        props[var_name] = value

                own_settings.save()
            except Exception:
                # Best effort: profile save should not block project creation.
                pass

        # POC runs should not write to the audit log or apply connection variables.
        # Note: custom hook handling happens after this block, so that POC can still
        # run the hook when enabled.
        if project_type == "POC":
            pass

        # Optional: write connection variables into the created project's global variables.
        # This is connection-agnostic: variable keys come from ${VAR} templates.
        # POC projects skip connection variable writes.
        if payload.snowflake_enabled and project_type != "POC":
            update: dict[str, str] = {}

            for row in payload.snowflake_rows:
                if not isinstance(row, dict) or not row.get("use"):
                    continue

                cells = row.get("cells")
                if not isinstance(cells, dict):
                    continue

                for cell in cells.values():
                    if not isinstance(cell, dict) or not cell.get("editable"):
                        continue

                    template = cell.get("template")
                    if not is_variable_token(template):
                        continue

                    value = cell.get("value")
                    if not isinstance(value, str):
                        continue
                    value = value.strip()

                    # Skip blanks (user may rely on existing defaults/profile).
                    if not value:
                        continue

                    var_name = extract_variable_name(str(template))
                    if var_name in update:
                        raise ValueError(
                            f"Connection variable conflict for {var_name}. "
                            "Multiple selected connections map to the same variable key."
                        )
                    update[var_name] = value

            if update:
                try:
                    project_handle.update_variables(update, type="standard")
                except Exception as e:
                    raise ValueError(
                        "Failed to write connection variables to the created project's global variables. "
                        f"Underlying error: {e}"
                    )

        hook_enabled = bool(isinstance(plugin_cfg, dict) and plugin_cfg.get("enable_custom_hook"))
        hook_runnable_type = (
            str(plugin_cfg.get("custom_hook_runnable_type") or "").strip()
            if isinstance(plugin_cfg, dict)
            else ""
        )
        hook_include_poc = bool(isinstance(plugin_cfg, dict) and plugin_cfg.get("custom_hook_include_poc"))

        should_run_hook = hook_enabled and hook_runnable_type and (project_type != "POC" or hook_include_poc)

        if should_run_hook:
            try:
                macro = self.admin_client.get_project(self.project_key).get_macro(hook_runnable_type)
                run_id = macro.run(params={}, wait=True)
                try:
                    hook_result = macro.get_result(run_id, as_type="json")
                except Exception:
                    hook_result = macro.get_result(run_id, as_type="string")

                hook_status = "ok"
                hook_error_str = ""

                if isinstance(hook_result, dict):
                    raw_status = hook_result.get("status")
                    if isinstance(raw_status, str) and raw_status.strip():
                        hook_status = raw_status.strip().lower()

                    if hook_status in {"warn", "warning"}:
                        hook_status = "warning"

                    if hook_status in {"error", "failed", "failure"}:
                        raw_error = hook_result.get("error")
                        raw_message = hook_result.get("message")

                        if isinstance(raw_error, str) and raw_error.strip():
                            hook_error_str = raw_error.strip()
                        elif isinstance(raw_message, str) and raw_message.strip():
                            hook_error_str = raw_message.strip()
                        else:
                            hook_error_str = to_json_str(hook_result)

                if hook_status in {"error", "failed", "failure"}:
                    # Roll back (clean failure: the hook returned a structured error)
                    if bronze_dataset is not None and bronze_row_base is not None and intake_run_id is not None:
                        try:
                            append_status(
                                bronze_dataset,
                                intake_run_id=intake_run_id,
                                intake_status="REVERTED",
                                base_row={**bronze_row_base, "project_key": self.project_key},
                                hook_runnable_type=hook_runnable_type,
                                hook_error=hook_error_str,
                            )
                        except Exception:
                            pass

                    try:
                        self.admin_client.get_project(self.project_key).delete(
                            clear_managed_datasets=True,
                            clear_output_managed_folders=True,
                            clear_job_and_scenario_logs=True,
                            wait=True,
                        )
                    except Exception:
                        pass

                    message = (
                        "Intake form successfully updated, project created, "
                        f"error running custom hook, reverting. {hook_error_str}"
                    )
                    return {
                        "projectKey": self.project_key,
                        "status": "reverted",
                        "logged": project_type != "POC",
                        "message": message,
                        "hook": {
                            "enabled": True,
                            "status": "error",
                            "error": hook_error_str,
                            "result": hook_result,
                            "reverted": True,
                        },
                    }

                if bronze_dataset is not None and bronze_row_base is not None and intake_run_id is not None:
                    append_status(
                        bronze_dataset,
                        intake_run_id=intake_run_id,
                        intake_status="HOOK_OK",
                        base_row={**bronze_row_base, "project_key": self.project_key},
                        hook_runnable_type=hook_runnable_type,
                    )

                message = "Project created."
                if isinstance(hook_result, dict):
                    maybe_message = hook_result.get("message")
                    if isinstance(maybe_message, str) and maybe_message.strip():
                        message = maybe_message.strip()

                # Preserve existing return contract while surfacing hook info.
                if project_type == "POC":
                    return {
                        "projectKey": self.project_key,
                        "status": "created",
                        "logged": False,
                        "message": message,
                        "hook": {"enabled": True, "status": hook_status, "result": hook_result},
                    }

                return {
                    "projectKey": self.project_key,
                    "status": "created",
                    "logged": True,
                    "message": message,
                    "hook": {"enabled": True, "status": hook_status, "result": hook_result},
                }

            except Exception as hook_error:
                hook_error_str = str(hook_error)

                # Best-effort: mark rollback in intake dataset (append-only)
                if bronze_dataset is not None and bronze_row_base is not None and intake_run_id is not None:
                    try:
                        append_status(
                            bronze_dataset,
                            intake_run_id=intake_run_id,
                            intake_status="REVERTED",
                            base_row={**bronze_row_base, "project_key": self.project_key},
                            hook_runnable_type=hook_runnable_type,
                            hook_error=hook_error_str,
                        )
                    except Exception:
                        pass

                # Roll back the project created by this macro.
                try:
                    self.admin_client.get_project(self.project_key).delete(
                        clear_managed_datasets=True,
                        clear_output_managed_folders=True,
                        clear_job_and_scenario_logs=True,
                        wait=True,
                    )
                except Exception:
                    pass

                # Return a UI-friendly error.
                message = (
                    "Intake form successfully updated, project created, "
                    f"error running custom hook, reverting. {hook_error_str}"
                )
                return {
                    "projectKey": self.project_key,
                    "status": "reverted",
                    "logged": project_type != "POC",
                    "message": message,
                    "hook": {
                        "enabled": True,
                        "status": "error",
                        "error": hook_error_str,
                        "reverted": True,
                    },
                }

        # No hook (or skipped)
        message = "Project created."

        if project_type == "POC":
            return {
                "projectKey": self.project_key,
                "status": "created",
                "logged": False,
                "message": message,
            }

        if bronze_dataset is not None and bronze_row_base is not None and intake_run_id is not None:
            append_status(
                bronze_dataset,
                intake_run_id=intake_run_id,
                intake_status="CREATED",
                base_row={**bronze_row_base, "project_key": self.project_key},
            )

        return {"projectKey": self.project_key, "status": "created", "logged": True, "message": message}
