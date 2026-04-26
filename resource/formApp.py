from __future__ import annotations

from projectvaluecapture.client_builder import (
    create_admin_client,
    create_user_client,
    enforce_project_create_groups,
)
from projectvaluecapture.new_project import build_project_key
from projectvaluecapture.snowflake_vars import (
    SNOWFLAKE_MAPPING_DATASET_DEFAULT,
    read_snowflake_mapping_rows,
)
from projectvaluecapture.form_choices import build_form_choices_response


def _get_bool(cfg, key: str, default: bool = False) -> bool:
    value = (cfg or {}).get(key, default)
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y"}
    if isinstance(value, int):
        return value != 0
    return default


def do(payload, config, plugin_config, inputs):
    """Return dropdown choices for the macro form.

    Dataiku passes plugin settings as `plugin_config`.

    This plugin intentionally does not fetch plugin settings via API or read local
    workspace extras files. If required fields are missing, fail fast with a
    clear error.
    """

    if not isinstance(plugin_config, dict) or not plugin_config:
        raise ValueError(
            "Missing plugin settings (plugin_config is empty). "
            "Configure the plugin settings in DSS (Plugin settings page)."
        )

    # Block unauthorized users before showing the form.
    # Don't raise here (it shows a scary stack trace in the UI).
    user_client = create_user_client()
    try:
        enforce_project_create_groups(user_client, plugin_config)
    except Exception as e:
        return {"authorized": False, "auth_error": str(e)}

    # Snowflake action endpoints (loads mapping rows / profile helpers)
    action = (payload or {}).get("action") if isinstance(payload, dict) else None

    if action == "snowflake_profile":
        try:
            own = user_client.get_own_user().get_settings()
            props = own.user_properties or {}
            if not isinstance(props, dict):
                props = {}

            var_names = (payload or {}).get("var_names") if isinstance(payload, dict) else None
            if not isinstance(var_names, list):
                var_names = []

            out: dict[str, str] = {}
            for var_name in var_names:
                if not isinstance(var_name, str) or not var_name.strip():
                    continue
                value = props.get(var_name)
                if isinstance(value, str) and value.strip():
                    out[var_name] = value

            return {"vars": out}
        except Exception as e:
            return {
                "vars": {},
                "profile_warning": f"Unable to load Snowflake defaults from user profile ({e}).",
            }

    if action == "snowflake":
        # Never raise from the form backend for this action: failures should be shown
        # as a user-friendly warning instead of a stack trace.
        try:
            if not _get_bool(plugin_config, "enable_snowflake_vars", False):
                return {"enable_snowflake_vars": False, "snowflake_rows": []}


            # Scope to user-visible Snowflake connections
            try:
                user_connections = user_client.list_connections_names("Snowflake") or []
            except Exception:
                user_connections = []

            if not user_connections:
                return {
                    "enable_snowflake_vars": True,
                    "snowflake_rows": [],
                    "snowflake_warning": (
                        "User does not have access to any Snowflake connection. "
                        "If you feel this is incorrect, please consult your Dataiku Administration Team."
                    ),
                }

            # Read hub mapping dataset using the admin client
            admin_client = create_admin_client(plugin_config)

            hub_name = (plugin_config or {}).get("hub_project_name") or "Project Value Hub"
            hub_key = build_project_key(str(hub_name), max_len=60)
            hub_project = admin_client.get_project(hub_key)

            dataset_name = (plugin_config or {}).get("snowflake_vars_dataset_name")
            if not isinstance(dataset_name, str) or not dataset_name.strip():
                dataset_name = SNOWFLAKE_MAPPING_DATASET_DEFAULT

            try:
                existing = {d.get("name") for d in (hub_project.list_datasets() or [])}
            except Exception:
                existing = set()

            if dataset_name not in existing:
                return {
                    "enable_snowflake_vars": True,
                    "snowflake_rows": [],
                    "snowflake_warning": (
                        "Snowflake variables are enabled, but the mapping dataset "
                        f"{dataset_name!r} was not found in the hub project. "
                        "Please consult your Dataiku Administration Team."
                    ),
                }

            mapping_ds = hub_project.get_dataset(dataset_name)
            mapping_rows = read_snowflake_mapping_rows(mapping_ds)

            if not mapping_rows:
                return {
                    "enable_snowflake_vars": True,
                    "snowflake_rows": [],
                    "snowflake_warning": (
                        "Snowflake variables are enabled, but the mapping dataset is empty (or missing required columns). "
                        "Please consult your Dataiku Administration Team."
                    ),
                }

            visible_by_lower = {
                c.strip().lower(): c.strip()
                for c in user_connections
                if isinstance(c, str) and c.strip()
            }

            out_rows = []
            for r in mapping_rows:
                key = r.connection_name.strip().lower()
                if key in visible_by_lower:
                    out_rows.append(
                        {
                            "connection_name": visible_by_lower[key],
                            "warehouse": r.warehouse,
                            "database": r.database,
                            "role": r.role,
                            "schema": r.schema,
                        }
                    )

            if not out_rows:
                mapped = sorted({r.connection_name for r in mapping_rows if r.connection_name})
                return {
                    "enable_snowflake_vars": True,
                    "snowflake_rows": [],
                    "snowflake_warning": (
                        "Snowflake variables are enabled, but none of your accessible Snowflake connections are present in the mapping dataset. "
                        f"Accessible: {', '.join(sorted(visible_by_lower.values()))}. "
                        f"Mapped: {', '.join(mapped)}."
                    ),
                }

            return {"enable_snowflake_vars": True, "snowflake_rows": out_rows}

        except Exception as e:
            # Make sure the UI always gets a response it can render.
            return {
                "enable_snowflake_vars": True,
                "snowflake_rows": [],
                "snowflake_warning": (
                    "Unable to load Snowflake connections. Please consult your Dataiku Administration Team. "
                    f"(Details: {e})"
                ),
            }

    choices = build_form_choices_response(plugin_config)

    if not choices.get("projTypes"):
        raise ValueError(
            "Plugin settings are missing form choice lists. "
            "Expected keys like fc_proj_types, fc_gbus, fc_business_users, "
            "fc_technical_users, fc_value_drivers, fc_non_fin_impact_levels."
        )

    return choices
