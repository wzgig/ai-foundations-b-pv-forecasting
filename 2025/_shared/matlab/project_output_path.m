function target = project_output_path(scriptPath, category, filename)
%PROJECT_OUTPUT_PATH Return a stable outputs/category/filename path.

if nargin < 2 || isempty(category)
    category = 'figures';
end

scriptDir = fileparts(scriptPath);
targetDir = fullfile(scriptDir, 'outputs', category);
if ~exist(targetDir, 'dir')
    mkdir(targetDir);
end
target = fullfile(targetDir, filename);
end
