# Custom Hook Macro (Customer Extension)

This plugin supports an **optional “custom hook” macro** that runs **inside the newly created project** after the standard project creation flow.

The goal is to let each customer implement environment-specific provisioning (ex: attach the project to Git, apply permissions, create managed folders, set bundle/template, etc.) **without modifying this plugin’s source code**.

## Summary

When enabled, the runnable executes this sequence:

1. **(Non-POC only)** Append an intake row to the hub intake dataset (`intake_status="STARTED"`).
2. **Create project** (standard plugin behavior).
3. **Run hook macro** in the *created* project (admin API key).
4. If hook fails: **revert** by:
   - appending an intake row (`intake_status="REVERTED"`) with `hook_error`
   - deleting the created project (including managed datasets/folders)

Notes:
- **POC projects are still not logged** to the intake dataset.
- The hook **may** run for POC projects if configured.

## Plugin Settings

Configure under **Plugin settings** (`plugin.json`):

- `enable_custom_hook` (BOOLEAN)
  - Enables running the hook macro.
- `custom_hook_runnable_type` (STRING)
  - The full runnable type identifier for the macro to run.
  - Example: `pyrunnable_instance-insights_project-advisor`
- `custom_hook_include_poc` (BOOLEAN)
  - If `true`, the hook runs for POC projects too.
  - POC projects still return `logged=false`.

### How to find `custom_hook_runnable_type`

The runnable type is the identifier used by the DSS API under:

`/projects/<PROJECT_KEY>/runnables/<RUNNABLE_TYPE>`

You can retrieve it via the Python API (example):

```python
import dataikuapi

client = dataikuapi.DSSClient("http://<dss-host>:<port>", api_key="<adminKey>")
proj = client.get_project("MYPROJECT")
for m in proj.list_macros():
    print(m["runnableType"], "-", m.get("label"))
```

## Execution Details

### Where the hook runs

The hook macro is invoked **in the newly created project**:

```python
macro = admin_client.get_project(created_project_key).get_macro(custom_hook_runnable_type)
run_id = macro.run(params={}, wait=True)
result = macro.get_result(run_id, as_type="json")
```

This is important for use cases like Git attachment, because the hook is operating with the created project as its context.

### Permissions model

The hook macro is invoked using the plugin’s **admin API key**, so it can perform administrative actions.

Treat the hook macro as **trusted customer code**.

## Intake Dataset Semantics (Non-POC)

The intake log is **append-only**.

A single “intake attempt” is identified by `intake_run_id` and can have multiple rows over time:

- `STARTED`: intake row written before project creation
- `CREATED`: project created successfully and no hook ran (disabled/skipped)
- `HOOK_OK`: hook completed successfully
- `REVERTED`: hook failed and the project was deleted

Additional columns:
- `hook_runnable_type`: the hook macro runnable type (if enabled)
- `hook_error`: error string captured on failure

### Reporting tip

When building reporting dashboards, **do not count raw rows**.

Instead, group by `intake_run_id` and take the **latest** row by `created_at`. Only count runs whose latest status is not `REVERTED`.

## Hook Macro “Contract” (Recommended)

The plugin will attempt to read the hook result as **JSON**, falling back to **string**.

### Hook result format (recommended)

If you return JSON, use this structure:

- `status` (string, required): one of `ok`, `warning`, `error`
  - `ok`: hook succeeded
  - `warning`: hook succeeded but wants to surface non-fatal warnings
  - `error`: hook wants the main macro to **revert** (project will be deleted)
- `message` (string, recommended): short user-facing summary
- `error` (string, required when `status=error`): clean error message
- `warnings` (list of strings, optional): non-fatal issues
- `links` (list of `{label, url}` objects, optional): URLs to repo, docs, tickets, etc.
- `outputs` (object, optional): structured outputs (repo name, branch, created objects)

If your hook raises an exception instead of returning JSON, the main macro will also treat it as a failure and revert.

### How the plugin interprets `status`

- If the hook **returns** JSON with `status="error"`:
  - the macro marks the intake run as `REVERTED`
  - deletes the created project
  - returns a clean error payload to the UI using the hook-provided `error` (or `message`)
- If the hook returns `status="warning"`:
  - the macro does **not** revert
  - the UI receives `hook.status="warning"` plus your full `hook.result`
- If the hook returns `status="ok"` (or no `status` field):
  - the macro does **not** revert

### Main macro return payload (JSON_OBJECT)

This runnable advertises `resultType: "JSON_OBJECT"` in `python-runnables/new-project-value-capture/runnable.json`.

On success, the runnable returns a JSON object containing:

- `projectKey` (string): created project key
- `status` (string): `"created"`
- `logged` (boolean): whether an intake row was written (false for POC)
- `message` (string): short human-readable summary (uses the hook’s `message` when present)
- `hook` (object, optional): present only when the hook is enabled and executed
  - `enabled` (boolean): true
  - `status` (string): `"ok"` or `"warning"`
  - `result` (object|string): the hook’s return value

On hook failure (exception or `status="error"`), the runnable returns:

- `projectKey` (string): the created project key (the macro then deletes it)
- `status` (string): `"reverted"`
- `logged` (boolean): whether an intake row was written
- `message` (string): `"Intake form successfully updated, project created, error running custom hook, reverting. <details>"`
- `hook.status` (string): `"error"`
- `hook.error` (string): captured error string
- `hook.result` (object|string, optional): included when the hook returned structured JSON
- The project is deleted (best effort)

### Example: success (`hook.status=ok`)

```json
{
  "projectKey": "MY_PROJECT",
  "status": "created",
  "logged": true,
  "message": "Attached project to Git and created default branches",
  "hook": {
    "enabled": true,
    "status": "ok",
    "result": {
      "status": "ok",
      "message": "Attached project to Git and created default branches",
      "links": [{"label": "Repo", "url": "https://github.com/acme/myrepo"}],
      "warnings": [],
      "outputs": {"repo": "acme/myrepo", "defaultBranch": "main"}
    }
  }
}
```

### Example: success with warnings (`hook.status=warning`)

```json
{
  "projectKey": "MY_PROJECT",
  "status": "created",
  "logged": true,
  "message": "Project created but Git attachment needs manual step",
  "hook": {
    "enabled": true,
    "status": "warning",
    "result": {
      "status": "warning",
      "message": "Project created but Git attachment needs manual step",
      "warnings": ["Git provider token not configured; skipping repo attach"],
      "links": [{"label": "How to configure Git", "url": "https://internal/wiki"}]
    }
  }
}
```

### Example: reverted (`hook.status=error`)

```json
{
  "projectKey": "MY_PROJECT",
  "status": "reverted",
  "logged": true,
  "message": "Intake form successfully updated, project created, error running custom hook, reverting. Missing Git token",
  "hook": {
    "enabled": true,
    "status": "error",
    "error": "Missing Git token",
    "result": {
      "status": "error",
      "message": "Cannot attach Git repo",
      "error": "Missing Git token"
    },
    "reverted": true
  }
}
```

Notes:
- The UI can render `message` as the primary line.
- `hook.result.links` and `hook.result.warnings` are passed through unchanged and can be rendered by a custom UI if desired.

### Recommended hook JSON result fields

If your hook macro returns JSON, keep it small and UI-friendly. Suggested keys:

- `status` (string): `ok`, `warning`, or `error`
- `message` (string): 1–2 sentence outcome
- `error` (string): only when `status=error` (clean rollback reason)
- `actions` (list of strings): major steps performed
- `links` (list of objects): clickable URLs to surfaced resources
  - `{ "label": "Git repo", "url": "https://..." }`
- `outputs` (object): structured outputs (repo name, branch, template ID, etc.)
- `warnings` (list of strings): non-fatal issues

Example:

```json
{
  "status": "ok",
  "message": "Attached project to Git and created default branches",
  "actions": ["git_attach", "create_branches"],
  "links": [{"label": "Repo", "url": "https://github.com/acme/myrepo"}],
  "outputs": {"repo": "acme/myrepo", "defaultBranch": "main"},
  "warnings": []
}
```

## Tips & Tricks for Hook Authors

- **Be idempotent**: assume the hook could be retried. If possible, detect “already attached” / “already created” and succeed.
- **Fail fast** with actionable errors: raise a clear exception when a required precondition is missing.
- **Avoid long-running work** where possible; if unavoidable, emit progress/logs from the macro side.
- **Don’t rely on intake logging** for POC: POC runs are not inserted into the hub dataset by this plugin.
- **Prefer returning JSON**: it’s surfaced back to the user under `hook.result`.

## Troubleshooting

- Hook does not run:
  - Ensure `enable_custom_hook=true`
  - Ensure `custom_hook_runnable_type` is non-empty and correct
  - If POC: ensure `custom_hook_include_poc=true`
- Hook fails with “not found”:
  - Ensure the macro is installed and accessible in the created project context
  - Confirm the runnable type string via `list_macros()`

