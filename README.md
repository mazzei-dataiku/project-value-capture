# project-value-capture (Dataiku DSS plugin)

This repository contains a Dataiku DSS plugin that provides a runnable (macro) with a custom intake form for creating new projects and capturing project metadata.

## What’s in this repo

- `python-runnables/new-project-value-capture/runnable.py`: runnable entrypoint (`MyRunnable`).
- `resource/formParamsTemplate.html`: AngularJS form template.
- `js/formParamsModule.js`: AngularJS controller logic.
- `resource/formApp.py`: server-side “form setup” returning choice lists from plugin settings (`fc_*`).
- `parameter-sets/form-choices/parameter-set.json`: plugin parameter set that defines the `fc_*` lists and their default values.
- `python-lib/`: shared helper code (importable in DSS plugin runtime).
- `unit_testing/new-project-value-capture.py`: minimal local harness to instantiate and run the runnable.

## Local configuration directory

This workspace uses an “extras” directory to store runnable configs:

- `/home/dataiku/workspace/project-lib-versioned/python/project-value-capture.extras/runnable-configs/config.json`
- `/home/dataiku/workspace/project-lib-versioned/python/project-value-capture.extras/runnable-configs/plugin_config.json`

`unit_testing/new-project-value-capture.py` loads these two files and passes them as `config` and `plugin_config` to `MyRunnable.__init__`.

### Plugin settings conventions

- DSS plugin settings are expected to provide the form choice lists as top-level lists prefixed with `fc_`:
  - `fc_proj_types`, `fc_gbus`, `fc_business_users`, `fc_technical_users`, `fc_value_drivers`, `fc_non_fin_impact_levels`
- `financial_value_drivers` is the subset of drivers that should use numeric USD input in the form.

**Parameter sets**

- `parameter-sets/form-choices/parameter-set.json` defines the plugin settings UI for these lists and provides `defaultValue` arrays.

**Local dev/testing**

- The workspace extras `plugin_config.json` still uses the wrapper format `{ "param1": { ... } }` as a workaround for a DSS password-encryption behavior.
- Admin API key for DSS admin client:
  - `admin_api_token` (required; stored as a password)

## Running the local harness

Use Dataiku’s bundled Python:

- `cd /home/dataiku/workspace/project-lib-versioned/python/project-value-capture`
- `/opt/dataiku/pyenv/bin/python unit_testing/new-project-value-capture.py`

Notes:
- The runnable uses a real admin API key from plugin settings. Local execution in Code Studio may still fail if that key is not available in your local extras config.

## Quick sanity check

- `/opt/dataiku/pyenv/bin/python -m compileall python-lib python-runnables resource unit_testing`
