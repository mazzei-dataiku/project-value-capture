// 1. IMPORTANT: Remove 'dataiku.services' from the brackets []. 
// This stops the $http error.
var app = angular.module('projectValueCaptureParams', []);

app.controller('ProjectValueCaptureParamsController', ['$scope', function($scope) {

    $scope.config = $scope.config || {};

    // Initialize default values
    $scope.config.projName = $scope.config.projName || '';
    $scope.config.projectDescription = $scope.config.projectDescription || '';
    $scope.config.projType = $scope.config.projType || '';
    $scope.config.idAPM = $scope.config.idAPM || '';
    $scope.config.gbu = $scope.config.gbu || '';

    $scope.config.businessOwner = $scope.config.businessOwner || [];
    $scope.config.technicalOwner = $scope.config.technicalOwner || [];
    $scope.config.customBusinessOwner = $scope.config.customBusinessOwner || '';
    $scope.config.customTechnicalOwner = $scope.config.customTechnicalOwner || '';

    $scope.config.problemStatement = $scope.config.problemStatement || '';
    $scope.config.solutionDescription = $scope.config.solutionDescription || '';

    $scope.config.labels = $scope.config.labels || [{label:""}];
    $scope.config.links = $scope.config.links || [{link:""}];
    $scope.config.drivers = $scope.config.drivers || [{driver:""}];
    $scope.config.impacts = $scope.config.impacts || [{impact:""}];

    // --- BACKEND HANDSHAKE ---
    var fetchInitChoices = function() {
        // $scope.callPythonDo is built-in; it doesn't need $http
        $scope.callPythonDo({}).then(function(data) {
            $scope.projTypes = data.projTypes;

            $scope.fc_gbus_enabled = data.fc_gbus_enabled;
            $scope.gbuOptions = data.GBUs;

            $scope.fc_business_users_enabled = data.fc_business_users_enabled;
            $scope.usersA = data.businessUsers;

            $scope.fc_technical_users_enabled = data.fc_technical_users_enabled;
            $scope.usersB = data.technicalUsers;

            $scope.fc_value_drivers_enabled = data.fc_value_drivers_enabled;
            $scope.driverOptions = data.valueDrivers;

            $scope.fc_non_fin_impact_levels_enabled = data.fc_non_fin_impact_levels_enabled;
            $scope.nonFinImpactOptions = data.nonFinImpactSize;

            $scope.financial_value_drivers_enabled = data.financial_value_drivers_enabled;
            $scope.financialValueDrivers = data.financialValueDrivers || [];
        }, function(err) {
            console.error("Backend failed to load choices", err);
        });
    };

    fetchInitChoices();

    // --- DYNAMIC TABLE LOGIC ---
    $scope.addLink = function() {
        $scope.config.labels.push({label:""});
        $scope.config.links.push({link:""});
    };
    $scope.deleteLink = function(index) {
        $scope.config.labels.splice(index, 1);
        $scope.config.links.splice(index, 1);
    };
    $scope.addDriver = function() {
      $scope.config.drivers.push({driver:""});
      $scope.config.impacts.push({impact:""});
    };
    $scope.deleteDriver = function(index) {
        $scope.config.drivers.splice(index, 1);
        $scope.config.impacts.splice(index, 1);
    };

    function buildOwners(selected, customText) {
        let final = angular.copy(selected || []);
        let idx = final.indexOf('Other');
        if (idx !== -1) {
            if (customText && customText.trim()) {
                final[idx] = customText.trim();
            }
        }
        return final.filter(function(v) { return typeof v === 'string' && v.trim(); });
    }

    function zipLinks(labels, links) {
        let out = [];
        for (let i = 0; i < Math.max((labels || []).length, (links || []).length); i++) {
            let label = (labels && labels[i]) ? labels[i].label : null;
            let url = (links && links[i]) ? links[i].link : null;
            if (label && typeof label === 'string' && label.trim()) {
                out.push({label: label.trim(), url: (url && typeof url === 'string') ? url.trim() : ''});
            }
        }
        return out;
    }

    function zipDrivers(drivers, impacts) {
        let out = [];
        for (let i = 0; i < Math.max((drivers || []).length, (impacts || []).length); i++) {
            let d = (drivers && drivers[i]) ? drivers[i].driver : null;
            let impact = (impacts && impacts[i]) ? impacts[i].impact : null;
            if (d && typeof d === 'string' && d.trim()) {
                out.push({driver: d.trim(), impact: impact});
            }
        }
        return out;
    }

    function recomputeDerived() {
        $scope.config.finalBusinessOwners = buildOwners($scope.config.businessOwner, $scope.config.customBusinessOwner);
        $scope.config.finalTechnicalOwners = buildOwners($scope.config.technicalOwner, $scope.config.customTechnicalOwner);
        $scope.config.finalZippedLinks = zipLinks($scope.config.labels, $scope.config.links);
        $scope.config.finalZippedDrivers = zipDrivers($scope.config.drivers, $scope.config.impacts);
    }

    // Keep derived fields in sync for the runnable
    $scope.$watchGroup(
        ['config.businessOwner', 'config.customBusinessOwner', 'config.technicalOwner', 'config.customTechnicalOwner'],
        function() { recomputeDerived(); },
        true
    );
    $scope.$watchGroup(['config.labels', 'config.links'], function() { recomputeDerived(); }, true);
    $scope.$watchGroup(['config.drivers', 'config.impacts'], function() { recomputeDerived(); }, true);

    recomputeDerived();
}]);
