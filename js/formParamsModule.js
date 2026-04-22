// Dataiku Webapp specific global function to get backend URL
// This is standard in Dataiku and allows JS to know where to send API calls.
const getBackendUrl = (path) => dataiku.getWebAppBackendUrl(path);

// --- Angular App Definition ---
// In DSS runnable custom forms, Dataiku's Angular services may be available.
let moduleDeps = [];
try {
    angular.module('dataiku.services');
    moduleDeps = ['dataiku.services'];
} catch (e) {
    moduleDeps = [];
}

var app = angular.module('formParams', moduleDeps);

app.controller('projectController', function($scope, $injector) {

    // Best-effort load of resolved plugin settings (may include decrypted PASSWORD values)
    // so we can pass required values to the runnable when DSS does not populate plugin_config.
    const DataikuAPI = ($injector && $injector.has && $injector.has('DataikuAPI')) ? $injector.get('DataikuAPI') : null;

    var fetchPluginSettings = function() {
        if (!DataikuAPI || !DataikuAPI.plugins || !DataikuAPI.plugins.getResolvedSettings) {
            return;
        }

        const pluginId = $scope.pluginId || 'project-value-capture';
        DataikuAPI.plugins.getResolvedSettings(pluginId).success(function(data) {
            // Do NOT console.log this object; it can contain secrets.
            const resolved = (data && (data.config || data)) || {};
            $scope.pluginConfig = resolved;

            // Provide admin_api_token to runnable via config as a fallback.
            // This is only used when DSS doesn't populate runnable plugin_config.
            if (!$scope.config.admin_api_token && resolved.admin_api_token) {
                $scope.config.admin_api_token = resolved.admin_api_token;
            }
        });
    };

    var fetchInitChoices = function() {
        $scope.callPythonDo({}).then(function(data) {
            // success
            $scope.projTypes = data.projTypes;

            $scope.fc_gbus_enabled = data.fc_gbus_enabled !== false;
            $scope.gbuOptions = data.GBUs;

            $scope.fc_business_users_enabled = data.fc_business_users_enabled !== false;
            $scope.usersA = data.businessUsers;

            $scope.fc_technical_users_enabled = data.fc_technical_users_enabled !== false;
            $scope.usersB = data.technicalUsers;

            $scope.fc_value_drivers_enabled = data.fc_value_drivers_enabled !== false;
            $scope.driverOptions = data.valueDrivers;

            $scope.fc_non_fin_impact_levels_enabled = data.fc_non_fin_impact_levels_enabled !== false;
            $scope.nonFinImpactOptions = data.nonFinImpactSize;

            $scope.financial_value_drivers_enabled = data.financial_value_drivers_enabled !== false;
            $scope.financialValueDrivers = data.financialValueDrivers || [];

            // Safety: ensure 'Other' exists even if backend forgot it
            if ($scope.usersA.indexOf('Other') === -1) $scope.usersA.push('Other');
            if ($scope.usersB.indexOf('Other') === -1) $scope.usersB.push('Other');
        }, function(data) {
            $scope.projTypes = [];

            $scope.fc_gbus_enabled = true;
            $scope.gbuOptions = [];

            $scope.fc_business_users_enabled = true;
            $scope.usersA = [];

            $scope.fc_technical_users_enabled = true;
            $scope.usersB = [];

            $scope.fc_value_drivers_enabled = true;
            $scope.driverOptions = [];

            $scope.fc_non_fin_impact_levels_enabled = true;
            $scope.nonFinImpactOptions = [];

            $scope.financial_value_drivers_enabled = true;
            $scope.financialValueDrivers = [];
        });
    };
    
    fetchInitChoices();
    fetchPluginSettings();
    
    $scope.config.projName = '';
    $scope.config.projectDescription = '';
    $scope.config.projType = '';
    // fallback for admin key if needed
    $scope.config.admin_api_token = '';
    
    $scope.config.idAPM = '';
    
    $scope.config.gbu = '';
    $scope.config.businessOwner = [];
    $scope.config.technicalOwner = [];
    $scope.config.customBusinessOwner = '';
    $scope.config.customTechnicalOwner = '';
    
    $scope.config.problemStatement = '';
    $scope.config.solutionDescription = '';
    
    $scope.config.labels=[{label:""}];
    $scope.config.links=[{link:""}];
    
    $scope.addLink = function(label, link) {
    $scope.config.labels.push({label:""});
    $scope.config.links.push({link:""});
    };
    
    $scope.deleteLink = function(label, link) {
        for(var i=0; i<$scope.config.labels.length; i++) {
          if($scope.config.labels[i] === label) {
            $scope.config.labels.splice(i, 1);
            $scope.config.links.splice(i, 1);
            break;
          }
        }
      };

    $scope.zippedLinks = function() {
        let newLinks = [];

        $scope.config.labels.forEach((item, index) => {
            if (!item || !item.label || item.label.trim() === '') {
                return;
            }

            let url = '';
            if ($scope.config.links[index] && $scope.config.links[index].link) {
                url = $scope.config.links[index].link;
            }

            newLinks.push({ label: item.label.trim(), url: (url || '').trim() });
        });

        return newLinks;
    };
    
    $scope.$watch(function() {
        return[$scope.config.labels, $scope.config.links];
    }, function(){
        $scope.config.finalZippedLinks = $scope.zippedLinks();
    }, true);
    
    
    $scope.config.drivers=[{driver:""}];
    $scope.config.impacts=[{impact:""}];
    
    $scope.addDriver = function(driver, impact) {
      $scope.config.drivers.push({driver:""});
      $scope.config.impacts.push({impact:""});
    };

    $scope.deleteDriver = function(driver, impact) {
      for(var i=0; i<$scope.config.drivers.length; i++) {
        if($scope.config.drivers[i] === driver) {
          $scope.config.drivers.splice(i, 1);
          $scope.config.impacts.splice(i, 1);
          break;
        }
      }
    };

    $scope.zippedDrivers = function() {
        let newDrivers = [];

        $scope.config.drivers.forEach((item, index) => {
            if (!item || !item.driver || item.driver.trim() === '') {
                return;
            }

            let impact = '';
            if ($scope.config.impacts[index]) {
                impact = $scope.config.impacts[index].impact;
            }

            newDrivers.push({ driver: item.driver.trim(), impact: impact });
        });

        return newDrivers;
    };
    
    $scope.$watch(function() {
            return[$scope.config.drivers, $scope.config.impacts];
        }, function(){
            $scope.config.finalZippedDrivers = $scope.zippedDrivers();
        }, true);

    
    $scope.$watch(function() {
        return [$scope.config.businessOwner, $scope.config.customBusinessOwner];
    }, function() {
        // 1. Create a deep copy so we don't accidentally mutate the UI dropdown state
        let finalBusOwners = angular.copy($scope.config.businessOwner || []);
        let customBusOwner = $scope.config.customBusinessOwner || "";

        // 2. Check if 'Other' is currently selected
        let otherBusIndex = finalBusOwners.indexOf('Other');

        if (otherBusIndex !== -1) {
            // 3. If 'Other' is selected AND they typed something, splice the custom text in
            if (customBusOwner.trim() !== '') {
                finalBusOwners.splice(otherBusIndex, 1, customBusOwner.trim());
            } else {
                // 4. If 'Other' is selected but the box is empty, just remove 'Other' from the final payload
                finalBusOwners.splice(otherBusIndex, 1);
            }
        }

        // 5. Save the merged result to your final variable
        $scope.config.finalBusinessOwners = finalBusOwners;

    }, true);
    
    $scope.$watch(function() {
        return [$scope.config.technicalOwner, $scope.config.customTechnicalOwner];
    }, function() {
        // 1. Create a deep copy so we don't accidentally mutate the UI dropdown state
        let finalTechOwners = angular.copy($scope.config.technicalOwner || []);
        let customTechOwner = $scope.config.customTechnicalOwner || "";

        // 2. Check if 'Other' is currently selected
        let otherTechIndex = finalTechOwners.indexOf('Other');

        if (otherTechIndex !== -1) {
            // 3. If 'Other' is selected AND they typed something, splice the custom text in
            if (customTechOwner.trim() !== '') {
                finalTechOwners.splice(otherTechIndex, 1, customTechOwner.trim());
            } else {
                // 4. If 'Other' is selected but the box is empty, just remove 'Other' from the final payload
                finalTechOwners.splice(otherTechIndex, 1);
            }
        }

        // 5. Save the merged result to your final variable
        $scope.config.finalTechnicalOwners = finalTechOwners;

    }, true);
    
    
});