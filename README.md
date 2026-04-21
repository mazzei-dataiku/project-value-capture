# project-value-capture (Dataiku DSS plugin)

This repository contains a Dataiku DSS plugin that provides a runnable (macro) with a custom intake form for creating new projects and capturing project metadata.

## What’s in this repo

- `python-runnables/new-project-value-capture/runnable.py`: runnable entrypoint (`MyRunnable`).
- `resource/formParamsTemplate.html`: AngularJS form template.
- `js/formParamsModule.js`: AngularJS controller logic.
- `resource/formApp.py`: server-side “form setup” returning choice lists.
- `python-lib/`: shared helper code (importable in DSS plugin runtime).
- `unit_testing/new-project-value-capture.py`: minimal local harness to instantiate and run the runnable.

## Local configuration directory

This workspace uses an “extras” directory to store runnable configs:

- `/home/dataiku/workspace/project-lib-versioned/python/project-value-capture.extras/runnable-configs/config.json`
- `/home/dataiku/workspace/project-lib-versioned/python/project-value-capture.extras/runnable-configs/plugin_config.json`

`unit_testing/new-project-value-capture.py` loads these two files and passes them as `config` and `plugin_config` to `MyRunnable.__init__`.

### `plugin_config.json` conventions

- Wrapper format: `{ "param1": { ... } }` (workaround for a DSS password-encryption behavior).
- Form choice lists are stored as top-level lists prefixed with `fc_`:
  - `fc_proj_types`, `fc_gbus`, `fc_business_users`, `fc_technical_users`, `fc_value_drivers`, `fc_non_fin_impact_levels`
- Admin token for DSS macro admin client:
  - `admin_api_token` (defaults to `creation1` if missing)

## Running the local harness

Use Dataiku’s bundled Python:

- `cd /home/dataiku/workspace/project-lib-versioned/python/project-value-capture`
- `/opt/dataiku/pyenv/bin/python unit_testing/new-project-value-capture.py`

Notes:
- If `runnable.py` calls `utils.get_admin_dss_client(...)`, local execution in Code Studio may fail because DSS macro runtime secrets are not present (missing `shared-secret.txt`). This is expected; the runnable is primarily designed to run inside DSS.

## Quick sanity check

- `/opt/dataiku/pyenv/bin/python -m compileall python-lib python-runnables resource unit_testing`
