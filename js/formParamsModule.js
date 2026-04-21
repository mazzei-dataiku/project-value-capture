// Dataiku Webapp specific global function to get backend URL
// This is standard in Dataiku and allows JS to know where to send API calls.
const getBackendUrl = (path) => dataiku.getWebAppBackendUrl(path);

// --- Angular App Definition ---
var app = angular.module('formParams', []);

app.controller('projectController', function($scope) {
    
    var fetchInitChoices = function() {
        $scope.callPythonDo({}).then(function(data) {
            // success
            $scope.projTypes = data.projTypes;
            $scope.gbuOptions = data.GBUs;
            $scope.usersA = data.businessUsers;
            $scope.usersB = data.technicalUsers;
            $scope.driverOptions = data.valueDrivers;
            $scope.nonFinImpactOptions = data.nonFinImpactSize;
            $scope.financialValueDrivers = data.financialValueDrivers || [];

            // Safety: ensure 'Other' exists even if backend forgot it
            if ($scope.usersA.indexOf('Other') === -1) $scope.usersA.push('Other');
            if ($scope.usersB.indexOf('Other') === -1) $scope.usersB.push('Other');
        }, function(data) {
            $scope.projTypes = [];
            $scope.gbuOptions = [];
            $scope.usersA = [];
            $scope.usersB = [];
            $scope.driverOptions = [];
            $scope.nonFinImpactOptions = [];
            $scope.financialValueDrivers = [];
        });
    };
    
    fetchInitChoices(); 
    
    $scope.config.projName = '';
    $scope.config.projType = '';
    
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