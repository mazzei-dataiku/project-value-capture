// 1. IMPORTANT: Remove 'dataiku.services' from the brackets []. 
// This stops the $http error.
var app = angular.module('projectValueCaptureParams', []);

app.controller('ProjectValueCaptureParamsController', ['$scope', function($scope) {

    $scope.config = $scope.config || {};

    $scope.notAuthorized = false;
    $scope.auth_error = '';
    $scope.loadingChoices = true;

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

    $scope.enable_snowflake_vars = false;
    $scope.snowflake_rows = [];
    $scope.snowflake_warning = '';

    $scope.config.useSnowflakeVars = $scope.config.useSnowflakeVars || false;
    $scope.config.loadSnowflakeFromProfile = $scope.config.loadSnowflakeFromProfile || false;
    $scope.config.saveSnowflakeToProfile = $scope.config.saveSnowflakeToProfile || false;
    $scope.config.snowflakeRows = $scope.config.snowflakeRows || [];

    // --- BACKEND HANDSHAKE ---
    var fetchInitChoices = function() {
        $scope.loadingChoices = true;
        // $scope.callPythonDo is built-in; it doesn't need $http
         $scope.callPythonDo({}).then(function(data) {
             if (data && data.authorized === false) {
                 $scope.notAuthorized = true;
                 $scope.auth_error = data.auth_error || 'You are not allowed to create projects.';
                 $scope.projTypes = [];
                 $scope.loadingChoices = false;
                 recomputeDerived();
                 return;
             }

             $scope.notAuthorized = false;
             $scope.projTypes = data.projTypes;
             $scope.enable_snowflake_vars = !!data.enable_snowflake_vars;
             $scope.loadingChoices = false;
 
 
            $scope.apm_id_enabled = !!data.apm_id_enabled;
            $scope.apm_id_project_types = data.apm_id_project_types || [];

             $scope.fc_gbus_enabled = data.fc_gbus_enabled;
             $scope.gbuOptions = data.GBUs;

             $scope.fc_business_users_enabled = data.fc_business_users_enabled;
             $scope.fc_technical_users_enabled = data.fc_technical_users_enabled;

             $scope.gbu_settings_map = data.gbu_settings_map || {};

             // Owner options are derived from selected GBU.
             $scope.usersA = [];
             $scope.usersB = [];

             if (($scope.config.gbu || '').toString().trim()) {
                 $scope.applyGbuOwners();
             } else {
                 recomputeDerived();
             }


            $scope.fc_value_drivers_enabled = data.fc_value_drivers_enabled;
            $scope.driverOptions = data.valueDrivers;

            $scope.fc_non_fin_impact_levels_enabled = data.fc_non_fin_impact_levels_enabled;
            $scope.nonFinImpactOptions = data.nonFinImpactSize;

            $scope.financial_value_drivers_enabled = data.financial_value_drivers_enabled;
            $scope.financialValueDrivers = data.financialValueDrivers || [];
         }, function(err) {
             $scope.loadingChoices = false;
             console.error("Backend failed to load choices", err);
         });
     };

    fetchInitChoices();

    function isVarToken(s) {
        return typeof s === 'string' && /^\$\{[A-Za-z_][A-Za-z0-9_]*\}$/.test(s.trim());
    }

    function extractVarName(token) {
        let s = (token || '').toString().trim();
        let m = /^\$\{([A-Za-z_][A-Za-z0-9_]*)\}$/.exec(s);
        return m ? m[1] : null;
    }

    function applySnowflakeProfileDefaults(defaults) {
        let vars = (defaults && defaults.vars && typeof defaults.vars === 'object') ? defaults.vars : {};

        ($scope.config.snowflakeRows || []).forEach(function(r) {
            if (!r) {
                return;
            }

            ['warehouse', 'database', 'role', 'schema'].forEach(function(field) {
                let cell = r[field];
                if (!cell || !cell.editable) {
                    return;
                }

                let varName = extractVarName(cell.template);
                if (!varName) {
                    return;
                }

                let v = vars[varName];
                if (typeof v === 'string') {
                    cell.value = v;
                }
            });
        });
    }

    $scope.loadSnowflakeFromProfile = function() {
        if (!$scope.config.useSnowflakeVars) {
            return;
        }
        let varNames = [];
        let seen = {};
        ($scope.config.snowflakeRows || []).forEach(function(r) {
            if (!r) {
                return;
            }
            ['warehouse', 'database', 'role', 'schema'].forEach(function(field) {
                let cell = r[field];
                if (!cell || !cell.editable) {
                    return;
                }
                let varName = extractVarName(cell.template);
                if (varName && !seen[varName]) {
                    seen[varName] = true;
                    varNames.push(varName);
                }
            });
        });

        $scope.callPythonDo({action: 'snowflake_profile', var_names: varNames}).then(function(data) {
            if (data && data.profile_warning) {
                $scope.snowflake_warning = data.profile_warning;
            }
            applySnowflakeProfileDefaults(data);
            recomputeDerived();
        }, function(err) {
            console.error('Backend failed to load user profile Snowflake defaults', err);
            $scope.snowflake_warning = 'Unable to load Snowflake defaults from user profile.';
            recomputeDerived();
        });
    };

     function ensureOtherOnlyIfEmpty(values) {
         let out = [];
         if (Array.isArray(values)) {
             values.forEach(function(v) {
                 if (typeof v === 'string' && v.trim()) {
                     out.push(v.trim());
                 }
             });
         }

         let hasOther = out.indexOf('Other') !== -1;
         if (out.length === 0) {
             return ['Other'];
         }
         if (!hasOther) {
             out.push('Other');
         }
         return out;
     }

     $scope.applyGbuOwners = function() {
         let gbu = ($scope.config.gbu || '').toString().trim();
         let mapping = $scope.gbu_settings_map || {};
         let conf = mapping[gbu] || {};

         $scope.usersA = ensureOtherOnlyIfEmpty(conf.businessUsers);
         $scope.usersB = ensureOtherOnlyIfEmpty(conf.technicalUsers);

         let prev = $scope._last_gbu_for_owners;
         $scope._last_gbu_for_owners = gbu;

         // Clear selected owners only when user changes GBU.
         if (typeof prev === 'string' && prev !== gbu) {
             $scope.config.businessOwner = [];
             $scope.config.technicalOwner = [];
             $scope.config.customBusinessOwner = '';
             $scope.config.customTechnicalOwner = '';
         }

         recomputeDerived();
     };

     $scope.toggleSnowflakeVars = function() {
         if (!$scope.config.useSnowflakeVars) {
             $scope.snowflake_rows = [];
             $scope.snowflake_warning = '';
             $scope.config.snowflakeRows = [];
             $scope.config.saveSnowflakeToProfile = false;
             recomputeDerived();
             return;
         }


        $scope.callPythonDo({action: 'snowflake'}).then(function(data) {
            $scope.enable_snowflake_vars = !!data.enable_snowflake_vars;
            $scope.snowflake_warning = data.snowflake_warning || '';
            $scope.snowflake_rows = data.snowflake_rows || [];

            $scope.config.snowflakeRows = ($scope.snowflake_rows || []).map(function(r) {
                function initCell(templateValue) {
                    let template = (templateValue || '').toString();
                    if (isVarToken(template)) {
                        return { template: template, value: '', editable: true };
                    }
                    return { template: template, value: template, editable: false };
                }

                return {
                    use: false,
                    connection_name: r.connection_name,
                    warehouse: initCell(r.warehouse),
                    database: initCell(r.database),
                    role: initCell(r.role),
                    schema: initCell(r.schema),
                };
            });

            if ($scope.config.loadSnowflakeFromProfile) {
                $scope.loadSnowflakeFromProfile();
                return;
            }

            recomputeDerived();
        }, function(err) {
            console.error('Backend failed to load Snowflake rows', err);
            $scope.snowflake_warning = 'Unable to load Snowflake connections. Please consult your Dataiku Administration Team.';
            $scope.snowflake_rows = [];
            $scope.config.snowflakeRows = [];
            recomputeDerived();
        });
    };

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

    function typeMatches(projectType, allowedTypes) {
        if (!projectType || typeof projectType !== 'string') {
            return false;
        }
        if (!Array.isArray(allowedTypes) || allowedTypes.length === 0) {
            return false;
        }
        let pt = projectType.trim().toLowerCase();
        return allowedTypes.some(function(t) {
            return typeof t === 'string' && t.trim().toLowerCase() === pt;
        });
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
        if ($scope.notAuthorized) {
            $scope.validation_errors = [];
            $scope.validation_state = {};
            return;
        }

        if ($scope.loadingChoices) {
            $scope.validation_errors = [];
            $scope.validation_state = {};
            return;
        }

        let snowflakeWarn = false;
        if ($scope.enable_snowflake_vars && $scope.config.useSnowflakeVars) {
            let rows = $scope.config.snowflakeRows || [];
            let selected = rows.filter(function(r) { return r && r.use; });
            if (selected.length === 0) {
                snowflakeWarn = true;
            }
        }


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

        let needsFull = !!$scope.config.projType && $scope.config.projType !== 'POC';

        if (needsFull) {
            let needsApm = $scope.apm_id_enabled && typeMatches($scope.config.projType, $scope.apm_id_project_types);
            if (needsApm) {
                let apmOk = ($scope.config.idAPM || '').trim().length > 0;
                state.idAPM = !apmOk;
                if (!apmOk) {
                    errors.push('APM ID is required for the selected Project Type.');
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

            // Snowflake vars validation (only when enabled + opted-in)
            if ($scope.enable_snowflake_vars && $scope.config.useSnowflakeVars) {
                let rows = $scope.config.snowflakeRows || [];
                let selected = rows.filter(function(r) { return r && r.use; });
                selected.forEach(function(r) {
                    let cn = r.connection_name || '';

                    function requireField(cell, label) {
                        if (!cell || !cell.editable) {
                            return;
                        }
                        let v = (cell.value || '').toString().trim();
                        if (!v) {
                            errors.push('Snowflake ' + label + ' is required for ' + cn + '.');
                        }
                    }

                    requireField(r.warehouse, 'warehouse');
                    requireField(r.database, 'database');
                    requireField(r.role, 'role');
                    // schema is optional
                });
            }
        }

        if (snowflakeWarn) {
            // Warning only; do not block project creation.
            errors.push('Snowflake variables enabled but no connections selected.');
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
