clear; clc; tic;

%% 读取数据
scriptDir = fileparts(mfilename('fullpath'));
projectRoot = fileparts(fileparts(scriptDir));
addpath(fullfile(projectRoot, '_shared', 'matlab'));
configure_journal_plot();
filename = resolve_project_input('station01.csv', scriptDir);
T = readtable(filename, 'VariableNamingRule', 'preserve');
T.date_time = datetime(T.date_time, 'InputFormat', 'yyyy/MM/dd HH:mm');

%% 异常值清洗
T(T.nwp_globalirrad <= 0, :) = [];
z_power = (T.power - mean(T.power)) ./ std(T.power);
T(abs(z_power) > 3, :) = [];
z_temp = (T.nwp_temperature - mean(T.nwp_temperature)) ./ std(T.nwp_temperature);
T(abs(z_temp) > 3, :) = [];

%% 图1：时间序列图
figure;
tiledlayout(4,1, 'Padding', 'compact', 'TileSpacing', 'compact');
nexttile; plot(T.date_time, T.power, 'k');
ylabel('发电功率 (MW)', 'Interpreter', 'none'); title('发电功率趋势', 'Interpreter', 'none'); grid on;
nexttile; plot(T.date_time, T.nwp_globalirrad, 'b');
ylabel('GHI (W/m^2)', 'Interpreter', 'none'); title('NWP 全球水平辐照', 'Interpreter', 'none'); grid on;
nexttile; plot(T.date_time, T.nwp_directirrad, 'r');
ylabel('DNI (W/m^2)', 'Interpreter', 'none'); title('NWP 法向直射辐照', 'Interpreter', 'none'); grid on;
nexttile; plot(T.date_time, T.nwp_temperature, 'm');
ylabel('气温 (℃)', 'Interpreter', 'none'); xlabel('时间', 'Interpreter', 'none'); title('NWP 气温', 'Interpreter', 'none'); grid on;
sgtitle('气象变量时间序列图', 'Interpreter', 'none');
save_project_figure(gcf, mfilename('fullpath'), 'figures', '01_时间序列图.png');

%% 图2：日内平均功率与GHI
T.HourMinute = timeofday(T.date_time);
[~, idx] = sort(T.HourMinute); T = T(idx,:);
daily = varfun(@mean, T, 'GroupingVariables','HourMinute', ...
    'InputVariables', {'power','nwp_globalirrad'});
figure;
yyaxis left; plot(daily.HourMinute, daily.mean_power, '-r');
ylabel('平均功率 (MW)', 'Interpreter', 'none');
yyaxis right; plot(daily.HourMinute, daily.mean_nwp_globalirrad, '-b');
ylabel('平均GHI (W/m^2)', 'Interpreter', 'none');
xlabel('一天中的时间', 'Interpreter', 'none');
title('一天中功率与GHI的平均变化', 'Interpreter', 'none');
legend({'功率','GHI'}, 'Location','northwest', 'Interpreter', 'none');
grid on;
save_project_figure(gcf, mfilename('fullpath'), 'figures', '02_日内平均曲线.png');

%% 图3：散点图
figure; tiledlayout(2,2, 'TileSpacing','compact');
vars = {'nwp_globalirrad','nwp_directirrad','nwp_temperature','nwp_humidity'};
titles = {'GHI 与功率','DNI 与功率','气温与功率','湿度与功率'};
xlabels = {'GHI (W/m^2)','DNI (W/m^2)','气温 (℃)','湿度 (%)'};
for i = 1:4
    nexttile;
    x = T.(vars{i}); y = T.power;
    scatter(x, y, 10, '.', 'MarkerEdgeAlpha', 0.3); hold on;
    p = polyfit(x, y, 1);
    plot(sort(x), polyval(p, sort(x)), 'r-', 'LineWidth', 1.2);
    xlabel(xlabels{i}, 'Interpreter', 'none');
    ylabel('功率 (MW)', 'Interpreter', 'none');
    title(titles{i}, 'Interpreter', 'none'); grid on;
end
sgtitle('功率与气象变量之间的关系', 'Interpreter', 'none');
save_project_figure(gcf, mfilename('fullpath'), 'figures', '03_功率散点图.png');

%% 图4：热力图（日-小时）
T.Date = dateshift(T.date_time, 'start', 'day');
T.Hour = hour(T.date_time);
Pmat = groupsummary(T, {'Date','Hour'}, 'mean', 'power');
heatData = unstack(Pmat, 'mean_power', 'Hour');
figure;
imagesc(0:23, datenum(heatData.Date), heatData{:,2:end});
colormap('hot'); colorbar;
xlabel('小时', 'Interpreter', 'none');
ylabel('日期', 'Interpreter', 'none');
datetick('y','mm月dd日','keepticks');
title('每日每小时平均发电功率热力图', 'Interpreter', 'none');
set(gca, 'YDir', 'normal');
save_project_figure(gcf, mfilename('fullpath'), 'figures', '04_热力图.png');

%% 图5：月均功率与GHI
T.Month = month(T.date_time);
monthly = varfun(@mean, T, 'GroupingVariables','Month', ...
    'InputVariables', {'power','nwp_globalirrad'});
figure;
yyaxis left
bar(monthly.Month, monthly.mean_power, 'FaceColor', [0.2 0.6 0.5], 'EdgeColor', 'k');
ylabel('平均功率 (MW)', 'Interpreter', 'none');
yyaxis right
plot(monthly.Month, monthly.mean_nwp_globalirrad, '-o', 'Color', [0.85 0.325 0.098], 'LineWidth', 2);
ylabel('平均GHI (W/m^2)', 'Interpreter', 'none');
xlabel('月份', 'Interpreter', 'none');
title('月均功率与GHI', 'Interpreter', 'none');
legend({'功率','GHI'}, 'Location','northwest', 'Interpreter', 'none'); grid on;
save_project_figure(gcf, mfilename('fullpath'), 'figures', '05_月均功率与GHI.png');

%% 图6：二维热图 GHI vs 温度
edges_GHI = 0:100:1200;
edges_Temp = 0:2:50;
avg_power_grid = NaN(length(edges_GHI)-1, length(edges_Temp)-1);
for i = 1:length(edges_GHI)-1
    for j = 1:length(edges_Temp)-1
        idx = T.nwp_globalirrad >= edges_GHI(i) & T.nwp_globalirrad < edges_GHI(i+1) & ...
              T.nwp_temperature >= edges_Temp(j) & T.nwp_temperature < edges_Temp(j+1);
        if any(idx)
            avg_power_grid(i,j) = mean(T.power(idx));
        end
    end
end
figure;
imagesc(edges_Temp(1:end-1)+1, edges_GHI(1:end-1)+50, avg_power_grid);
colorbar; colormap('jet');
xlabel('气温 (℃)', 'Interpreter', 'none'); ylabel('GHI (W/m^2)', 'Interpreter', 'none');
title('GHI 与温度条件下的平均功率热图', 'Interpreter', 'none');
set(gca, 'YDir', 'normal');
save_project_figure(gcf, mfilename('fullpath'), 'figures', '06_GHI_温度_热图.png');

%% 图7：月叠加 GHI 曲线
T.HourDecimal = hour(T.date_time) + minute(T.date_time)/60;
figure; hold on;
for m = 1:12
    Tm = T(T.Month == m, :);
    [~, idx] = sort(Tm.HourDecimal); Tm = Tm(idx, :);
    grp = varfun(@mean, Tm, 'GroupingVariables','HourDecimal', ...
        'InputVariables','nwp_globalirrad');
    plot(grp.HourDecimal, grp.mean_nwp_globalirrad);
end
xlabel('小时', 'Interpreter', 'none');
ylabel('平均GHI (W/m^2)', 'Interpreter', 'none');
L = findobj(gca, 'Type', 'Line');
legend(L(end:-1:1), arrayfun(@(x)sprintf('%d月',x),1:length(L),'UniformOutput',false), ...
    'Location','northeast', 'Interpreter','none');
title('各月日照典型曲线', 'Interpreter', 'none'); grid on;
save_project_figure(gcf, mfilename('fullpath'), 'figures', '07_各月GHI曲线.png');

%% 图8：温度 vs 单位辐照功率
eff = T.power ./ T.nwp_globalirrad;
valid_idx = isfinite(eff) & eff > 0 & eff < 1;
Teff = T(valid_idx, :); eff = eff(valid_idx);
edges = 0:2:50;
[~,~,bin] = histcounts(Teff.nwp_temperature, edges);
valid = bin > 0;
eff_avg = accumarray(bin(valid), eff(valid), [], @mean);
min_len = min(length(edges)-1, length(eff_avg));
figure;
plot(edges(1:min_len)+1, eff_avg(1:min_len), '-o');
xlabel('气温 (℃)', 'Interpreter', 'none');
ylabel('单位辐照功率（效率）', 'Interpreter', 'none');
title('温度对发电效率的影响', 'Interpreter', 'none'); grid on;
save_project_figure(gcf, mfilename('fullpath'), 'figures', '08_效率_vs_温度.png');

toc;
