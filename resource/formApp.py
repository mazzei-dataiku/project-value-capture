from __future__ import annotations

import dataiku

from dataiku.runnables import utils

from projectvaluecapture.config import load_plugin_config_from_path
from projectvaluecapture.form_choices import as_choices_dict


def do(payload, confic, plugin_config, inputs):
    # Keep the form setup lightweight and config-driven.
    # Do not reach into DSS projects/datasets here.
    cfg = load_plugin_config_from_path()

    choices = as_choices_dict(cfg.form_choices)
    choices["financialValueDrivers"] = cfg.financial_value_drivers

    return choices
