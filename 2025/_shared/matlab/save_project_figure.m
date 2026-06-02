function target = save_project_figure(figHandle, scriptPath, category, filename)
%SAVE_PROJECT_FIGURE Save a MATLAB figure under outputs/ with journal defaults.

if nargin < 1 || isempty(figHandle)
    figHandle = gcf;
end
if nargin < 3 || isempty(category)
    category = 'figures';
end

configure_journal_plot();
target = project_output_path(scriptPath, category, filename);
set(figHandle, 'Color', 'w');

try
    exportgraphics(figHandle, target, 'Resolution', 600);
catch
    print(figHandle, target, '-dpng', '-r600');
end
end
