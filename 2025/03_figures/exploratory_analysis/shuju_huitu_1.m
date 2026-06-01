clear,clc,tic
%% 数据读取与预处理
scriptDir = fileparts(mfilename('fullpath'));
projectRoot = fileparts(fileparts(scriptDir));
addpath(fullfile(projectRoot, '_shared', 'matlab'));
filename = resolve_project_input('Solar station site 5 (Nominal capacity-110MW).xlsx', scriptDir);
T = readtable(filename);

% 重命名字段
T.Properties.VariableNames = {'Time','TotalIrradiance','DNI','GHI','Temp','Pressure','Humidity','Power'};

% 时间格式转换
T.Time = datetime(T.Time, 'InputFormat', 'yyyy-MM-dd HH:mm:ss');

%% 图1：时间序列趋势图（使用 tiledlayout）
figure;
tiledlayout(4,1, 'Padding', 'compact', 'TileSpacing', 'compact');

nexttile; plot(T.Time, T.Power, 'LineWidth', 1.2); ylabel('Power (MW)');
title('发电功率'); set(gca, 'FontSize', 12); grid on;

nexttile; plot(T.Time, T.GHI, 'LineWidth', 1.2); ylabel('GHI (W/m^2)');
title('水平总辐照'); set(gca, 'FontSize', 12); grid on;

nexttile; plot(T.Time, T.DNI, 'LineWidth', 1.2); ylabel('DNI (W/m^2)');
title('直射法线辐照'); set(gca, 'FontSize', 12); grid on;

nexttile; plot(T.Time, T.Temp, 'LineWidth', 1.2); ylabel('Temp (°C)');
xlabel('时间'); title('气温'); set(gca, 'FontSize', 12); grid on;

sgtitle('光伏电站关键变量的时间序列趋势图', 'FontSize', 14);

%% 图2：日内平均功率与GHI曲线
T.HourMinute = timeofday(T.Time);
[~, idx] = sort(T.HourMinute);
T = T(idx,:);

dayProfiles = varfun(@mean, T, 'GroupingVariables','HourMinute', ...
    'InputVariables', {'Power','GHI'});

figure;
yyaxis left;
plot(dayProfiles.HourMinute, dayProfiles.mean_Power, 'r-', 'LineWidth', 1.5);
ylabel('平均功率 (MW)');

yyaxis right;
plot(dayProfiles.HourMinute, dayProfiles.mean_GHI, 'b-', 'LineWidth', 1.5);
ylabel('平均GHI (W/m^2)');

xlabel('一天中的时间'); title('日内平均功率与GHI变化');
legend('Power', 'GHI'); grid on; set(gca, 'FontSize', 12);

%% 图3：散点图与变量关系
figure;
tiledlayout(2,2, 'TileSpacing','compact');

nexttile; scatter(T.GHI, T.Power, 8, '.', 'MarkerEdgeAlpha', 0.5);
xlabel('GHI (W/m^2)'); ylabel('Power (MW)'); title('GHI vs Power'); grid on;

nexttile; scatter(T.DNI, T.Power, 8, '.', 'MarkerEdgeAlpha', 0.5);
xlabel('DNI (W/m^2)'); ylabel('Power (MW)'); title('DNI vs Power'); grid on;

nexttile; scatter(T.Temp, T.Power, 8, '.', 'MarkerEdgeAlpha', 0.5);
xlabel('Temp (°C)'); ylabel('Power (MW)'); title('Temp vs Power'); grid on;

nexttile; scatter(T.Humidity, T.Power, 8, '.', 'MarkerEdgeAlpha', 0.5);
xlabel('Humidity (%)'); ylabel('Power (MW)'); title('Humidity vs Power'); grid on;

sgtitle('功率与气象变量的关系散点图', 'FontSize', 14);

%% 图4：二维热力图（日 vs 小时）
T.Date = dateshift(T.Time, 'start', 'day');
T.Hour = hour(T.Time);

powerMatrix = groupsummary(T, {'Date','Hour'}, 'mean', 'Power');
heatData = unstack(powerMatrix, 'mean_Power', 'Hour');

figure;
imagesc(0:23, datenum(heatData.Date), heatData{:,2:end});
colormap(parula); colorbar;
xlabel('小时'); ylabel('日期');
datetick('y','mmm dd','keepticks');
title('日-时二维热力图：平均功率');
set(gca, 'FontSize', 12);

%% 图5：月均功率与GHI柱图
T.Month = month(T.Time);
monthlyStat = varfun(@mean, T, 'GroupingVariables','Month', ...
    'InputVariables', {'Power','GHI'});

figure;
yyaxis left;
bar(monthlyStat.Month, monthlyStat.mean_Power, 'FaceColor', [0.2 0.6 0.5]);
ylabel('平均功率 (MW)');

yyaxis right;
plot(monthlyStat.Month, monthlyStat.mean_GHI, 'r-o', 'LineWidth', 1.5);
ylabel('平均GHI (W/m^2)');

xlabel('月份'); grid on;
title('月均功率与GHI变化');
legend('Power', 'GHI', 'Location', 'northwest');
set(gca, 'FontSize', 12);

toc
