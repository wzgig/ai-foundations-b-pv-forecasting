function filePath = resolve_project_input(fileName, startDir, fallbackNames)
%RESOLVE_PROJECT_INPUT Find a data file from a script directory and project fallbacks.
%
% filePath = resolve_project_input(fileName, startDir)
% filePath = resolve_project_input(fileName, startDir, fallbackNames)

if nargin < 2 || isempty(startDir)
    startDir = pwd;
end

if nargin < 3
    fallbackNames = {};
elseif ischar(fallbackNames) || isstring(fallbackNames)
    fallbackNames = cellstr(fallbackNames);
end

rootDir = find_2025_root(startDir);
names = [{char(fileName)}, fallbackNames(:)'];
searchDirs = {
    startDir, ...
    fullfile(rootDir, '01_modeling_workspace', 'pvod_full_experiment'), ...
    fullfile(rootDir, '02_problem_solutions', 'problem1_data_analysis'), ...
    fullfile(rootDir, '02_problem_solutions', 'problem2_baseline_forecasting'), ...
    fullfile(rootDir, '02_problem_solutions', 'problem3_scenario_analysis'), ...
    fullfile(rootDir, '02_problem_solutions', 'problem4_feature_ablation')
};

for i = 1:numel(names)
    for j = 1:numel(searchDirs)
        candidate = fullfile(searchDirs{j}, names{i});
        if exist(candidate, 'file')
            filePath = candidate;
            return;
        end
    end
end

error('resolve_project_input:FileNotFound', ...
    'Cannot find %s from %s or project fallbacks.', fileName, startDir);
end

function rootDir = find_2025_root(startDir)
current = char(startDir);
while true
    [parentDir, currentName] = fileparts(current);
    if strcmp(currentName, '2025') || ...
            (exist(fullfile(current, '02_problem_solutions'), 'dir') && ...
             exist(fullfile(current, '01_modeling_workspace'), 'dir'))
        rootDir = current;
        return;
    end

    if isempty(parentDir) || strcmp(parentDir, current)
        break;
    end
    current = parentDir;
end

error('resolve_project_input:RootNotFound', ...
    'Cannot locate the 2025 project root from %s.', startDir);
end
