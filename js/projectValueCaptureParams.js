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
        recomputeDerived();
    };
    $scope.deleteLink = function(index) {
        $scope.config.labels.splice(index, 1);
        $scope.config.links.splice(index, 1);
        recomputeDerived();
    };
    $scope.addDriver = function() {
      $scope.config.drivers.push({driver:""});
      $scope.config.impacts.push({impact:""});
      recomputeDerived();
    };
    $scope.deleteDriver = function(index) {
        $scope.config.drivers.splice(index, 1);
        $scope.config.impacts.splice(index, 1);
        recomputeDerived();
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

    function validateConfig() {
        let errors = [];
        let state = {};

        let projNameOk = ($scope.config.projName || '').trim().length > 0;
        state.projName = !projNameOk;
        if (!projNameOk) {
            errors.push('Project Name is required.');
        }

        let projTypeOk = ($scope.config.projType || '').trim().length > 0;
        state.projType = !projTypeOk;
        if (!projTypeOk) {
            errors.push('Project Type is required.');
        }

        let needsFull = $scope.config.projType === 'Industrialization' || $scope.config.projType === 'Ad-Hoc';

        if (needsFull) {
            if ($scope.config.projType === 'Industrialization') {
                let apmOk = ($scope.config.idAPM || '').trim().length > 0;
                state.idAPM = !apmOk;
                if (!apmOk) {
                    errors.push('APM ID is required for Industrialization.');
                }
            }

            if ($scope.fc_gbus_enabled) {
                let gbuOk = ($scope.config.gbu || '').trim().length > 0;
                state.gbu = !gbuOk;
                if (!gbuOk) {
                    errors.push('GBU is required.');
                }
            }

            if ($scope.fc_business_users_enabled) {
                let businessOk = Array.isArray($scope.config.finalBusinessOwners) && $scope.config.finalBusinessOwners.length > 0;
                state.businessOwner = !businessOk;
                if (!businessOk) {
                    errors.push('At least one Business Owner is required.');
                }
            }

            if ($scope.fc_technical_users_enabled) {
                let technicalOk = Array.isArray($scope.config.finalTechnicalOwners) && $scope.config.finalTechnicalOwners.length > 0;
                state.technicalOwner = !technicalOk;
                if (!technicalOk) {
                    errors.push('At least one Technical Owner is required.');
                }
            }

            let problemOk = ($scope.config.problemStatement || '').trim().length > 0;
            state.problemStatement = !problemOk;
            if (!problemOk) {
                errors.push('Problem Statement is required.');
            }

            let solutionOk = ($scope.config.solutionDescription || '').trim().length > 0;
            state.solutionDescription = !solutionOk;
            if (!solutionOk) {
                errors.push('Solution Description is required.');
            }

            if ($scope.fc_value_drivers_enabled) {
                let driversOk = Array.isArray($scope.config.finalZippedDrivers) && $scope.config.finalZippedDrivers.length > 0;
                state.valueDrivers = !driversOk;
                if (!driversOk) {
                    errors.push('At least one Value Driver is required.');
                }
            }
        }

        $scope.validation_errors = errors;
        $scope.validation_state = state;
    }

    function recomputeDerived() {
        $scope.config.finalBusinessOwners = buildOwners($scope.config.businessOwner, $scope.config.customBusinessOwner);
        $scope.config.finalTechnicalOwners = buildOwners($scope.config.technicalOwner, $scope.config.customTechnicalOwner);
        $scope.config.finalZippedLinks = zipLinks($scope.config.labels, $scope.config.links);
        $scope.config.finalZippedDrivers = zipDrivers($scope.config.drivers, $scope.config.impacts);
        validateConfig();
    }

    $scope.recomputeDerived = recomputeDerived;

    recomputeDerived();

}]);
