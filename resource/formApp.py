import dataiku
from dataiku.runnables import utils

def do(payload, confic, plugin_config, inputs):
    user_client = dataiku.api_client()
    user_auth_info = user_client.get_auth_info()
    admin_client = utils.get_admin_dss_client("data_fetch", user_auth_info)
    
    value_proj = admin_client.get_project('PROJECTVALUEHUB')
    params_df = value_proj.get_dataset("all_parameters").get_as_core_dataset().get_dataframe()
    
    choices = dict()
    choices['projTypes'] = list(params_df['project_types'].dropna().unique())
    choices['GBUs'] = list(params_df['GBUs'].dropna().unique())
    choices['businessUsers'] = list(params_df['business_user_displayname'].dropna().unique())
    choices['technicalUsers'] = list(params_df['technical_user_displayname'].dropna().unique())
    choices['valueDrivers'] = list(params_df['value_driver'].dropna().unique())
    choices['nonFinImpactSize'] = list(params_df['nonfinancial_impact_level'].dropna().unique())
    
    return choices
    