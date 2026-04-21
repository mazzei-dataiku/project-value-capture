from __future__ import annotations

import re


_PROJECT_KEY_ALLOWED_RE = re.compile(r"[^A-Z0-9_]")


def to_dss_project_key(name: str) -> str:
    """Convert an arbitrary label to a DSS-safe project key.

    Rules (conservative):
    - Uppercase
    - Whitespace -> underscore
    - Remove non [A-Z0-9_]
    - Collapse multiple underscores
    """

    if not isinstance(name, str):
        raise ValueError("Project name must be a string")

    value = name.strip().upper()
    if not value:
        raise ValueError("Project name must be non-empty")

    value = re.sub(r"\s+", "_", value)
    value = _PROJECT_KEY_ALLOWED_RE.sub("", value)
    value = re.sub(r"_+", "_", value).strip("_")

    if not value:
        raise ValueError("Project name did not produce a valid DSS project key")

    # DSS keys can be long, but keep it sane.
    return value[:64]
