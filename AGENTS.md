# AGENTS.md

Instructions for agentic coding assistants working in this repository.

This repo is a **Dataiku DSS plugin** (macro/runnable + webapp UI) stored under the Code Studio-synced folder `project-lib-versioned/python/project-value-capture/`.

## Project Layout

- `plugin.json`: plugin metadata (id/version/label).
- `python-runnables/new-project-value-capture/`: Python runnable (macro) implementation.
  - `runnable.json`: runnable descriptor (UI wiring, permissions, result type).
  - `runnable.py`: runnable code executed by DSS.
- `resource/`: runnable UI assets.
  - `formParamsTemplate.html`: AngularJS template for parameters.
  - `style.css`: UI styling.
  - `formApp.py`: Python setup for the parameter form (returns choices).
- `js/`: AngularJS module code used by the parameter form (`projectValueCaptureParams.js`).
- `python-lib/`: shared Python library code (importable package).
  - `projectvaluecapture/payload.py`: payload normalization + validation.
  - `projectvaluecapture/bronze.py`: hub bronze dataset create/append.
  - `projectvaluecapture/snowflake_vars.py`: hub Snowflake mapping dataset parsing.
- `unit_testing/`: local Code Studio harness script(s) for smoke testing.

## Environment / Prereqs (Dataiku Code Studio)

- Prefer Dataiku’s bundled env: `PYTHON=/opt/dataiku/pyenv/bin/python`.
- `python` may not exist on PATH; always use the absolute interpreter.
- Dataiku library import should work: `import dataiku`.
- Standard packaging configs (`pyproject.toml`, `setup.cfg`, etc.) are not present.

## Configs (Local / Extras)

This repo uses a workspace-side config directory (not necessarily shipped with the plugin):

- `project-lib-versioned/python/project-value-capture.extras/runnable-configs/config.json`
- `project-lib-versioned/python/project-value-capture.extras/runnable-configs/plugin_config.json`

### `plugin_config.json` shape

- Uses a wrapper object like `{ "param1": { ... } }`.
- The inner object contains values used by the plugin.
- Form choice lists are stored as top-level lists with an `fc_` prefix:
  - `fc_proj_types`, `fc_gbus`, `fc_business_users`, `fc_technical_users`, `fc_value_drivers`, `fc_non_fin_impact_levels`
- Defaults for these lists are defined in plugin settings (`plugin.json`) via `defaultValue`.
- Admin API key is stored as `admin_api_token` (required; no default).

## Build / Lint / Test

This plugin repo currently ships **no formal test/lint harness** (no `pytest`, `ruff`, `black`, `pre-commit` configs in-repo).

### Quick sanity checks

- **Syntax-check all Python files** (no execution):
  - `/opt/dataiku/pyenv/bin/python -m compileall python-lib python-runnables resource unit_testing`

- **Import-check the runnable module** (import only):
  - `/opt/dataiku/pyenv/bin/python -c "import importlib.util; import pathlib; p=pathlib.Path('python-runnables/new-project-value-capture/runnable.py'); spec=importlib.util.spec_from_file_location('runnable', p); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); print('ok')"`

### Local harness (Code Studio)

- Run the minimal local harness:
  - `/opt/dataiku/pyenv/bin/python unit_testing/new-project-value-capture.py`

Notes:
- The runnable uses a real admin API key from plugin settings; it does not rely on `utils.get_admin_dss_client(...)`.
- When run locally in Code Studio, the harness may print a `shared-secret.txt` missing error; that’s expected.

### Running the plugin (DSS)

- Install the plugin in DSS.
- Run the runnable `New Project` from the DSS UI.
- Validate:
  - the form populates choices from `plugin_config.json`
  - submission triggers project creation / logging as expected.

## Code Style Guidelines

### General

- Keep plugin components (runnables, form setup) **thin**; put reusable logic in `python-lib/`.
- Prefer small, testable helper functions over large `run()` bodies.
- Avoid “magic strings”: centralize dataset names, project keys, variable keys in config.

### Python

**Imports**

- Group imports: stdlib → third-party → `dataiku`.
- Prefer explicit imports over wildcard.

**Formatting**

- 4-space indentation.
- Keep lines ~88–100 chars where reasonable.

**Types**

- No enforced type checking.
- Add lightweight type hints at module boundaries when helpful.

**Naming**

- Modules/packages: `snake_case`.
- Functions/variables: `snake_case`.
- Classes: `PascalCase`.
- Constants: `UPPER_SNAKE_CASE`.

**Error handling**

- Prefer `ValueError`/`Exception` over `NameError` for validation failures.
- Validate early and fail fast with actionable messages.

### JavaScript / AngularJS (Dataiku plugin UI)

- Keep controller state in `$scope.config`.
- Prefer `const`/`let` over `var` for new code.
- Avoid expensive deep watches unless necessary.

### HTML/CSS

- Keep template readable; avoid logic in templates.
- Prefer scoped CSS classes (e.g. `.custom-*`) to avoid DSS style collisions.

## Editor/Agent Rules

- No Cursor rules found (`.cursor/rules/` or `.cursorrules` absent).
- No Copilot instructions found (`.github/copilot-instructions.md` absent).

## Repo Constraints (Code Studio)

- Files at the workspace root are not synced to DSS; work inside the synced plugin folder.
- Don’t add new “recipe” definitions via filesystem; create them in DSS.
