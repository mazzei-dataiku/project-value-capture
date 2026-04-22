from __future__ import annotations

from projectvaluecapture.form_choices import build_form_choices_response


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

    choices = build_form_choices_response(plugin_config)

    if not choices.get("projTypes"):
        raise ValueError(
            "Plugin settings are missing form choice lists. "
            "Expected keys like fc_proj_types, fc_gbus, fc_business_users, "
            "fc_technical_users, fc_value_drivers, fc_non_fin_impact_levels."
        )

    return choices
