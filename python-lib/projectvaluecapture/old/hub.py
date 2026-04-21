from __future__ import annotations

from projectvaluecapture.dss_naming import to_dss_project_key


def ensure_hub_project(admin_client, hub_project_name: str, hub_project_owner: str):
    hub_key = to_dss_project_key(hub_project_name)

    try:
        return admin_client.get_project(hub_key)
    except Exception:
        # If it doesn't exist, create it.
        project = admin_client.create_project(
            project_key=hub_key,
            name=hub_project_name,
            owner=hub_project_owner,
        )
        return project
