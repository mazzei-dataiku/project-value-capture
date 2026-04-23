from __future__ import annotations

import json
import sys
from pathlib import Path


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}

    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        return {}

    return json.loads(raw)


def main() -> None:
    base_dir = Path(__file__).resolve().parents[1]

    # Make plugin code importable (DSS runtime normally does this).
    sys.path.insert(0, str(base_dir / "python-lib"))
    sys.path.insert(0, str(base_dir / "python-runnables" / "new-project-value-capture"))

    from runnable import MyRunnable  # noqa: E402

    configs_dir = Path(
        "/home/dataiku/workspace/project-lib-versioned/python/project-value-capture.extras/"
        "runnable-configs"
    )
    config = _load_json(configs_dir / "config.json")
    plugin_config = _load_json(configs_dir / "plugin_config.json")

    # Keep unit testing config aligned with the current payload contract.
    # The runnable expects zipped lists under these keys.
    config.setdefault("projName", "Unit Test Project")
    config.setdefault("projType", "Ad-Hoc")
    config.setdefault("gbu", "Digital")
    config.setdefault("finalBusinessOwners", ["Unit Tester"])
    config.setdefault("finalTechnicalOwners", ["Unit Tester"])
    config.setdefault("problemStatement", "Unit test")
    config.setdefault("solutionDescription", "Unit test")
    config.setdefault("finalZippedLinks", config.get("finalZippedLinks") or [])
    config.setdefault("finalZippedDrivers", config.get("finalZippedDrivers") or [{"driver": "Increase Revenue", "impact": "Unknown"}])
    config.setdefault("useSnowflakeVars", False)
    config.setdefault("snowflakeRows", [])

    try:
        runnable = MyRunnable(project_key="DATA_COLLECTION", config=config, plugin_config=plugin_config)
        print(runnable.run(lambda _: None))
    except FileNotFoundError as e:
        # Expected outside the DSS macro runtime.
        print(e)


if __name__ == "__main__":
    main()
