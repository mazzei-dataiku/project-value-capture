# project-value-capture (Dataiku DSS plugin)

This repository contains a Dataiku DSS plugin that provides a runnable (macro) with a custom intake form for creating new projects and capturing project metadata.

## What’s in this repo

- `python-runnables/new-project-value-capture/runnable.py`: runnable entrypoint (`MyRunnable`).
- `python-runnables/new-project-value-capture/runnable.json`: runnable descriptor (template/module wiring).
- `resource/formParamsTemplate.html`: AngularJS form template.
- `js/projectValueCaptureParams.js`: AngularJS controller logic.
- `resource/formApp.py`: server-side “form setup” returning choice lists from plugin settings (`fc_*`).
- `python-lib/`: shared helper code (importable in DSS plugin runtime).
  - `python-lib/projectvaluecapture/form_choices.py`: maps plugin settings → UI choice lists.
  - `python-lib/projectvaluecapture/payload.py`: normalizes & validates submitted form payload.
  - `python-lib/projectvaluecapture/bronze.py`: creates/appends to the hub “bronze” intake log dataset.
- `unit_testing/new-project-value-capture.py`: minimal local harness to instantiate and run the runnable.

## Plugin settings

Plugin settings are defined in `plugin.json`.

### Snowflake variables (optional)

If `enable_snowflake_vars` is enabled, the form can optionally prompt for Snowflake connection variables and write them to the created project's global variables (`standard`).

- The mapping is read from a hub project dataset (`snowflake_vars_dataset_name`, default `snowflake_connnection_vars_map`).
- Expected columns: `connection_name`, `warehouse`, `database`, `role`, `schema`.
- Cells using the exact form `${VAR_NAME}` are treated as variable keys and become editable in the form.
- Cells not using `${...}` are treated as hard-coded display values and are not written to project variables.

Notes:
- The mapping dataset is read using the admin API key.
- Snowflake variable writing is skipped for `POC` projects.

### Form choice lists

Choice lists are expected as top-level lists prefixed with `fc_`:

- `fc_proj_types`, `fc_gbus`, `fc_business_users`, `fc_technical_users`, `fc_value_drivers`, `fc_non_fin_impact_levels`
- `financial_value_drivers` is the subset of drivers that should use numeric USD input in the form.

## Local configuration directory (Code Studio)

This workspace can use an “extras” directory to store runnable configs for local execution:

- `/home/dataiku/workspace/project-lib-versioned/python/project-value-capture.extras/runnable-configs/config.json`
- `/home/dataiku/workspace/project-lib-versioned/python/project-value-capture.extras/runnable-configs/plugin_config.json`

`unit_testing/new-project-value-capture.py` loads these files and passes them as `config` and `plugin_config` to `MyRunnable.__init__`.

Notes:
- In DSS runtime, plugin settings are passed in as `plugin_config`.
- Local extras `plugin_config.json` may use a wrapper format like `{ "param1": { ... } }`.

## Troubleshooting

- **Value Drivers required**: for project type `Ad-Hoc` and `Industrialization`, at least one value driver is required (validated in `python-lib/projectvaluecapture/payload.py`).
- **Hub bronze dataset creation requires a connection**: managed dataset creation may require an explicit connection; the plugin infers one and falls back to `filesystem_managed` (see `python-lib/projectvaluecapture/bronze.py`).

## Running the local harness

Use Dataiku’s bundled Python:

- `cd /home/dataiku/workspace/project-lib-versioned/python/project-value-capture`
- `/opt/dataiku/pyenv/bin/python unit_testing/new-project-value-capture.py`

## Quick sanity check

- `/opt/dataiku/pyenv/bin/python -m compileall python-lib python-runnables resource unit_testing`
