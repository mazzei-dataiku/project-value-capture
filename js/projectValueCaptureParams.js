// 1. IMPORTANT: Remove 'dataiku.services' from the brackets []. 
// This stops the $http error.
var app = angular.module('projectValueCaptureParams', []);

app.controller('ProjectValueCaptureParamsController', ['$scope', function($scope) {
    
    $scope.config = $scope.config || {};
    
    // Initialize default values
    $scope.config.projName = '';
    $scope.config.projectDescription = '';
    $scope.config.projType = '';
    $scope.config.idAPM = '';
    $scope.config.gbu = '';
    $scope.config.businessOwner = [];
    $scope.config.technicalOwner = [];
    $scope.config.customBusinessOwner = '';
    $scope.config.customTechnicalOwner = '';
    $scope.config.problemStatement = '';
    $scope.config.solutionDescription = '';
    $scope.config.labels = [{label:""}];
    $scope.config.links = [{link:""}];
    $scope.config.drivers = [{driver:""}];
    $scope.config.impacts = [{impact:""}];

    // --- BACKEND HANDSHAKE ---
    var fetchInitChoices = function() {
        // $scope.callPythonDo is built-in; it doesn't need $http
        $scope.callPythonDo({}).then(function(data) {
            $scope.projTypes = data.projTypes;
            $scope.gbuOptions = data.GBUs;
            $scope.usersA = data.businessUsers;
            $scope.usersB = data.technicalUsers;
            $scope.driverOptions = data.valueDrivers;
            $scope.nonFinImpactOptions = data.nonFinImpactSize;
            $scope.financialValueDrivers = data.financialValueDrivers || [];

            if ($scope.usersA && $scope.usersA.indexOf('Other') === -1) $scope.usersA.push('Other');
            if ($scope.usersB && $scope.usersB.indexOf('Other') === -1) $scope.usersB.push('Other');
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

    // --- "OTHER" BOX SYNC ---
    $scope.$watch('config.businessOwner', function() {
        let final = angular.copy($scope.config.businessOwner || []);
        let idx = final.indexOf('Other');
        if (idx !== -1 && $scope.config.customBusinessOwner) {
            final[idx] = $scope.config.customBusinessOwner;
        }
        $scope.config.finalBusinessOwners = final;
    }, true);
}]);