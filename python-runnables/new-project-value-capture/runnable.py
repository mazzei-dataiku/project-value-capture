# This file is the actual code for the Python runnable new-project-value-form
from dataiku.runnables import Runnable
from dataiku.runnables import utils
from datetime import datetime
import dataiku
import json
import pandas as pd

class MyRunnable(Runnable):
    """The base interface for a Python runnable"""

    def __init__(self, project_key, config, plugin_config):
        """
        :param project_key: the project in which the runnable executes
        :param config: the dict of the configuration of the object
        :param plugin_config: contains the plugin settings
        """
#         self.project_key = project_key
        self.config = config
        self.plugin_config = plugin_config
        
    def get_progress_target(self):
        """
        If the runnable will return some progress info, have this function return a tuple of 
        (target, unit) where unit is one of: SIZE, FILES, RECORDS, NONE
        """
        return None

    def run(self, progress_callback):
        """
        Do stuff here. Can return a string or raise an exception.
        The progress_callback is a function expecting 1 value: current progress
        """
        user_client = dataiku.api_client()
        user_auth_info = user_client.get_auth_info()
        admin_client = utils.get_admin_dss_client("creation1", user_auth_info)
        project_title = self.config.get('projName', None)
              
        project_key = ''.join(i for i in project_title if i.isalnum()).upper()
       
        project_type = self.config.get('projType', None)
        APM_ID = self.config.get('idAPM', None)
        GBU = self.config.get('gbu', None)
        business_owner = self.config.get('finalBusinessOwners', None)
        technical_owner = self.config.get('finalTechnicalOwners', None)
        problem_statement = self.config.get('problemStatement', None)
        solution_description = self.config.get('solutionDescription', None)
        final_zipped_links = self.config.get('finalZippedLinks', None)
        final_zipped_drivers = self.config.get('finalZippedDrivers', None)
        
        # Run completeness checks
        print(f"DEBUG: SELF-CONFIG == {self.config}")           
        if not project_type:
            raise NameError("You forgot to select a Project Type. Please fix to proceed.")
        elif project_type in ["Ad-Hoc", "Industrialization"]:
            if (project_type == "Industrialization") and not APM_ID:
                raise NameError("You forgot to provide your APM ID. Please fix to proceed.")
            elif not GBU:
                raise NameError("You forgot to select a GBU. Please fix to proceed.")
            elif not business_owner:
                raise NameError("You forgot to select one or more business owners. Please fix to proceed.")
            elif not technical_owner:
                raise NameError("You forgot to select one or more technical owners. Please fix to proceed.")
            elif not problem_statement:
                raise NameError("You forgot to provide a Problem Statement. Please fix to proceed.")
            elif not solution_description:
                raise NameError("You forgot to select a Solution Description. Please fix to proceed.")
            elif not final_zipped_drivers:
                raise NameError("You forgot to provide your project's Value Drivers. Please fix to proceed.")
        
        
#         project = admin_client.get_project(project_key)

        # Create the project
#         username = re.sub(r'[^a-zA-Z]', '', user_auth_info['authIdentifier']).upper()

        new_project_key = utils.make_unique_project_key(admin_client, f"{project_key}" )
#         project.duplicate(target_project_key = new_project_key, 
#                           target_project_name = f"{project.get_metadata()['label']} {username}", 
#                           duplication_mode='FULL', 
#                           target_project_folder=project_folder)

        # Insert record into Value Insights Tool project logging dataset
        value_proj = admin_client.get_project('PROJECTVALUEHUB')
        datasets_list = [i['name'] for i in value_proj.list_datasets()]

        new_project_row = {'projectKey': [new_project_key], 
                           'projectName': [project_title], 
                           'creator':[user_auth_info['authIdentifier']], 
                           'type': [project_type], 
                           'createdDate': [datetime.now()],
                           'APM_ID': [APM_ID],
                           'GBU': [GBU],
                           'businessOwners': [business_owner],
                           'technicalOwners': [technical_owner],
                           'problemStatement': [problem_statement],
                           'solutionDescription': [solution_description],
                           'Links': [final_zipped_links],
                           'valueDrivers': [final_zipped_drivers]}
        print(new_project_row)

        if "projects_log" not in datasets_list:
            # Create dataset if it does't already exist
            builder = value_proj.new_managed_dataset("projects_log")
            builder.with_store_into(value_proj.get_variables()['standard']['default_connection'])
            dataset = builder.create(overwrite=False)

            dataset_settings = dataset.get_settings()
            dataset_settings.add_raw_schema_column({"name": "projectKey", "type": 'string'})
            dataset_settings.add_raw_schema_column({"name": "projectName", "type": 'string'})
            dataset_settings.add_raw_schema_column({"name": "creator", "type": 'string'})
            dataset_settings.add_raw_schema_column({"name": "type", "type": 'string'})
            dataset_settings.add_raw_schema_column({"name": "createdDate", "type": 'string'})
            dataset_settings.add_raw_schema_column({"name": "APM_ID", "type": 'string'})
            dataset_settings.add_raw_schema_column({"name": "GBU", "type": 'string'})
            dataset_settings.add_raw_schema_column({"name": "businessOwners", "type": 'array'})
            dataset_settings.add_raw_schema_column({"name": "technicalOwners", "type": 'array'})
            dataset_settings.add_raw_schema_column({"name": "problemStatement", "type": 'string'})
            dataset_settings.add_raw_schema_column({"name": "solutionDescription", "type": 'string'})
            dataset_settings.add_raw_schema_column({"name": "Links", "type": 'array'})
            dataset_settings.add_raw_schema_column({"name": "valueDrivers", "type": 'array'})
            dataset_settings.save()

        # Fetch projects_log dataset from Value Insights Tool project and appends this project entry
        proj_log = value_proj.get_dataset("projects_log").get_as_core_dataset()
        proj_log.spec_item["appendMode"] = True
        proj_log.write_with_schema(pd.DataFrame.from_dict(new_project_row))

        # Actual project creation left until last in case other issues arise
        project = user_client.create_project(project_key=new_project_key,
                                    name=new_project_key,
                                    owner=user_auth_info['authIdentifier'])

        # Setting metadata TODO item
        metadata = project.get_metadata()

        if project_type == 'Industrialization':
            # TODO: replace with real webapp link once it's up
            metadata['checklists']['checklists'].append({'title': 'Project Documentation', 'items': [{'text': 'Update project value capture entry in [WebApp](web_app:PROJECTVALUEHUB.NGogdna)'}]})
            project.set_metadata(metadata)

#         project_permissions = new_project.get_permissions()
#         project_permissions['permissions'] = []
#         project_permissions['owner'] = user_auth_info['authIdentifier']
#         new_project.set_permissions(project_permissions)

        return json.dumps({"projectKey": new_project_key})
        