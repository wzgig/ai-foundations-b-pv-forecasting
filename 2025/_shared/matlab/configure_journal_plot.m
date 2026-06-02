function configure_journal_plot()
%CONFIGURE_JOURNAL_PLOT Apply Chinese journal-style MATLAB figure defaults.
%
% Use this at the beginning of MATLAB plotting scripts.  It keeps figures
% printable, high-contrast, and consistent with the Python plotting style.

set(0, 'defaultFigureColor', 'w');
set(0, 'defaultAxesFontName', 'Microsoft YaHei');
set(0, 'defaultTextFontName', 'Microsoft YaHei');
set(0, 'defaultAxesFontSize', 11);
set(0, 'defaultTextFontSize', 11);
set(0, 'defaultAxesLineWidth', 0.9);
set(0, 'defaultLineLineWidth', 1.8);
set(0, 'defaultAxesBox', 'on');
set(0, 'defaultAxesGridLineStyle', '--');
set(0, 'defaultAxesGridAlpha', 0.25);
set(0, 'defaultLegendBox', 'off');
set(0, 'defaultFigureUnits', 'centimeters');
set(0, 'defaultFigurePosition', [4, 4, 16, 10]);
end
