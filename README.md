# Project Value Capture (Dataiku DSS plugin)

This plugin adds a **"New Project" macro** to Dataiku DSS that helps teams **standardize project intake** and **capture business value** at the moment a project is created.

It is designed for project sponsors, managers, and delivery teams who want consistent answers to:

- What are we building?
- Why does it matter?
- Who owns it?
- What value do we expect to deliver?

## What you get

- **Guided intake form** for new projects (name, type, owners, problem/solution, links)
- **Value capture** through configurable Value Drivers and impact inputs
- **Audit trail**: submitted intake is logged into a hub project dataset (for reporting and governance)
- **Configurable dropdowns**: admins can manage Project Types, GBUs, owners lists, value drivers, etc.
- **Optional Snowflake variable support** (for environments that use per-project variables for Snowflake connections)

## Snowflake variables (optional)

Some organizations use **project-level variables** (like warehouse/database/role) to control Snowflake access.

When enabled by your administrators, the macro can:

- Ask whether you want to provide Snowflake variables for this project
- Show a table of Snowflake connections and the variables to fill
- Write the entered values into the created project’s variables

In addition, the form can optionally:

- **Load from User Profile**: quickly pre-fill variable values you commonly use
- **Save to User Profile**: remember your values for next time

## Who configures what

- **End users / managers**: fill out the intake form when creating a project
- **Administrators**: configure plugin settings (hub project, logging dataset, available choices, optional Snowflake behaviors)

## More documentation

- Developer-oriented documentation: `docs/developers_guide.md`
