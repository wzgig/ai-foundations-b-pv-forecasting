% 数据读取与预处理
filename = 'Solar station site 4 (Nominal capacity-130MW).xlsx';
T = readtable(filename);

% 重命名字段以方便调用
T.Properties.VariableNames = {'Time','TotalIrradiance','DNI','GHI','Temp','Pressure','Humidity','Power'};

% 时间格式处理
T.Time = datetime(T.Time, 'InputFormat', 'yyyy-MM-dd HH:mm:ss');

% --- 图1：时间序列趋势图 ---
figure;
subplot(4,1,1);
plot(T.Time, T.Power); title('功率 (MW)'); ylabel('MW');
grid on;

subplot(4,1,2);
plot(T.Time, T.GHI); title('GHI (W/m^2)'); ylabel('GHI');
grid on;

subplot(4,1,3);
plot(T.Time, T.DNI); title('DNI (W/m^2)'); ylabel('DNI');
grid on;

subplot(4,1,4);
plot(T.Time, T.Temp); title('气温 (°C)'); ylabel('Temp');
xlabel('时间'); grid on;

sgtitle('光伏电站关键变量的时间序列趋势图');

% --- 图2：日内平均功率与GHI ---
T.HourMinute = timeofday(T.Time);
[~, idx] = sort(T.HourMinute);
T = T(idx,:);

dayProfiles = varfun(@mean, T, 'GroupingVariables','HourMinute', ...
    'InputVariables', {'Power','GHI'});

figure;
plot(dayProfiles.HourMinute, dayProfiles.mean_Power, 'r-', 'LineWidth', 1.5); hold on;
plot(dayProfiles.HourMinute, dayProfiles.mean_GHI, 'b-', 'LineWidth', 1.5);
xlabel('一天中的时间'); ylabel('平均值');
legend('功率 (MW)', 'GHI (W/m^2)');
title('日内平均功率与水平辐照度变化');
grid on;

% --- 图3：散点图 ---
figure;
subplot(2,2,1); scatter(T.GHI, T.Power, 10, '.'); xlabel('GHI'); ylabel('Power'); title('GHI vs Power');
subplot(2,2,2); scatter(T.DNI, T.Power, 10, '.'); xlabel('DNI'); ylabel('Power'); title('DNI vs Power');
subplot(2,2,3); scatter(T.Temp, T.Power, 10, '.'); xlabel('Temperature'); ylabel('Power'); title('Temp vs Power');
subplot(2,2,4); scatter(T.Humidity, T.Power, 10, '.'); xlabel('Humidity'); ylabel('Power'); title('Humidity vs Power');
sgtitle('功率与气象变量的关系散点图');

% --- 图4：热力图 ---
T.Date = dateshift(T.Time, 'start', 'day');
T.Hour = hour(T.Time);

% 汇总为平均值矩阵
powerMatrix = groupsummary(T, {'Date','Hour'}, 'mean', 'Power');
heatData = unstack(powerMatrix, 'mean_Power', 'Hour');

figure;
imagesc(0:23, datenum(heatData.Date), heatData{:,2:end});
colormap(jet); colorbar;
datetick('y','mmm dd','keepticks');
xlabel('小时'); ylabel('日期');
title('日-时二维热力图：平均功率');

% --- 图5：月均统计图 ---
T.Month = month(T.Time);
monthlyStat = varfun(@mean, T, 'GroupingVariables','Month', ...
    'InputVariables', {'Power','GHI'});

figure;
yyaxis left;
bar(monthlyStat.Month, monthlyStat.mean_Power);
ylabel('平均功率 (MW)');

yyaxis right;
plot(monthlyStat.Month, monthlyStat.mean_GHI, 'r-o', 'LineWidth', 1.5);
ylabel('平均GHI (W/m^2)');

xlabel('月份'); grid on;
title('月均功率与水平辐照度变化');
legend('Power', 'GHI');
