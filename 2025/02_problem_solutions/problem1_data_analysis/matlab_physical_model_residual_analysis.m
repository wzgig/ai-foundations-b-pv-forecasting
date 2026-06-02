clear; clc; tic;

%% ------------------------ 1. 读取与预处理数据 ------------------------
%读取数据
scriptDir = fileparts(mfilename('fullpath'));
projectRoot = fileparts(fileparts(fileparts(scriptDir)));
addpath(fullfile(projectRoot, '_shared', 'matlab'));
filename = resolve_project_input('Solar station site 5 (Nominal capacity-110MW).xlsx', scriptDir);
% 保留原始变量名，避免 MATLAB 自动更改列名
T = readtable(filename, 'VariableNamingRule', 'preserve');  
% 重命名列变量，统一格式
T.Properties.VariableNames = {'Time','TotalIrradiance','DNI','GHI','Temp','Pressure','Humidity','Power'};
% 转换时间字符串为 datetime 类型
T.Time = datetime(T.Time, 'InputFormat', 'yyyy-MM-dd HH:mm:ss');
%% ------------------------ 2. 固定参数设置 ------------------------
A = 36666.667;         % 光伏阵列总面积（110MW换算）
beta = 31.17;          % 面板倾角
phi_p = 180;           % 面板朝向角（正南）
rho_g = 0.2;           % 地表反射率
eta_ref = 0.18;        % 组件标准效率
gamma = 0.0035;        % 温度效率衰减系数
kappa = 0.02;          % 温升系数
tau_a = 0.15;          % 气溶胶光学厚度
U_o = 0.3;             % 臭氧柱浓度

%% ------------------------ 3. 太阳位置与时间修正 ------------------------
latitude = 31.1708218;  longitude = 115.0159244;
d = day(T.Time,'dayofyear');  % 年中第几天
h = hour(T.Time) + minute(T.Time)/60 + second(T.Time)/3600;  % UTC小时
lat = deg2rad(latitude);  lon = longitude;

B = 2*pi*(d - 81)/364;
EoT = 9.87*sin(2*B) - 7.53*cos(B) - 1.5*sin(B);  % 时间方程
LSTM = 15 * round(lon/15);
TC = 4*(lon - LSTM) + EoT; LST = h + TC/60;

HRA = deg2rad(15*(LST - 12));  % 时角
delta = deg2rad(23.45)*sin(2*pi*(284+d)/365);  % 赤纬角

% 太阳高度角与天顶角
sin_alpha = sin(lat).*sin(delta) + cos(lat).*cos(delta).*cos(HRA);
alpha = asin(sin_alpha); zenith = rad2deg(pi/2 - alpha);

% 方位角
cos_Az = (sin(delta) - sin(lat).*sin_alpha) ./ (cos(lat).*cos(alpha));
cos_Az = min(max(cos_Az, -1), 1);  % 限制在 acos 有效范围
Az_rad = acos(cos_Az);
phi_s = rad2deg(Az_rad);
phi_s(h > 12) = 360 - phi_s(h > 12);
theta_z = zenith;  % 天顶角

%% ------------------------ 4. 入射角与辐照度计算 ------------------------
cos_theta_i = cosd(theta_z) .* cosd(beta) + ...
              sind(theta_z) .* sind(beta) .* cosd(phi_s - phi_p);
cos_theta_i = max(cos_theta_i, 0.05);  % 弱入射保留

T.DHI = max(T.GHI - T.DNI .* cosd(theta_z), 0);  % 漫射辐射

%% ------------------------ 5. 空气质量与大气透射率 ------------------------
m = 1 ./ (cosd(theta_z) + 0.50572 .* (96.07995 - theta_z).^(-1.6364));
m(isnan(m) | isinf(m)) = 10;

Tr = exp(-0.0903 .* (T.Pressure ./ 1013.25).^0.84 ./ (1 + cosd(theta_z)).^1.01);
Ta = exp(-tau_a .* (0.6777 + 0.1464*tau_a - 0.00626*tau_a.^2) .* m);
To = 1 - 0.011 .* (U_o .* m) ./ (1 + 0.006 .* (U_o .* m).^1.5);
Uw = 0.1 .* T.Humidity .* exp(0.07 .* T.Temp);
Tw = 1 - 0.077 .* (Uw .* m).^0.3;
Tg = exp(-0.0117 .* m.^0.3139);
Tatm = Tr .* Ta .* To .* Tw .* Tg;

%% ------------------------ 6. 有效辐照度与功率计算 ------------------------
G_eff = T.DNI .* cos_theta_i + ...
        T.DHI .* (1 + cosd(beta)) / 2 + ...
        rho_g .* T.GHI .* (1 - cosd(beta)) / 2;
Tatm = 0.8;
G_eff_corr = Tatm .* G_eff;
eta = eta_ref .* (1 - gamma .* (T.Temp + kappa .* T.GHI - 25));
eta = 0.22;
T.TheoPower = eta .* G_eff_corr .* A / 1e6;  % 单位 MW

%% ------------------------ 7. 数据清洗 ------------------------
T.Power = real(double(T.Power));
T.TheoPower = real(double(T.TheoPower));
validIdx = isfinite(T.Power) & isfinite(T.TheoPower);
daylight = T.GHI > 0;  % 白昼筛选

%% ------------------------ 8. 可视化分析 ------------------------

% 8.1 实际 vs 理论 功率时序图
figure;
plot(T.Time(validIdx), T.Power(validIdx), 'r-', 'LineWidth', 1); hold on;
plot(T.Time(validIdx), T.TheoPower(validIdx), 'k--', 'LineWidth', 1);
legend('实际功率', '理论功率');
xlabel('时间'); ylabel('功率 (MW)');
title('实际功率 vs 理论功率（时序）');
grid on;

% 8.2 月平均功率对比
T.Month = month(T.Time);
monthly = varfun(@mean, T, 'GroupingVariables','Month', ...
    'InputVariables', {'Power','TheoPower'});
figure;
bar(monthly.Month, [monthly.mean_Power, monthly.mean_TheoPower]);
legend('实际功率', '理论功率');
xlabel('月份'); ylabel('月均功率 (MW)');
title('季节性变化分析');
grid on;

% 8.3 日内平均功率曲线
T.HourMinute = timeofday(T.Time);
profile = varfun(@mean, T, 'GroupingVariables','HourMinute', ...
    'InputVariables', {'Power','TheoPower'});
figure;
plot(profile.HourMinute, profile.mean_Power, 'r-', 'LineWidth', 1.5); hold on;
plot(profile.HourMinute, profile.mean_TheoPower, 'k--', 'LineWidth', 1.5);
legend('实际功率', '理论功率');
xlabel('一天中的时间'); ylabel('平均功率 (MW)');
title('日内短周期波动分析');
grid on;

%% ------------------------ 9. 偏差指标计算（白昼） ------------------------
P_obs = T.Power(daylight);
P_theo = T.TheoPower(daylight);
rmse = sqrt(mean((P_obs - P_theo).^2));
mae = mean(abs(P_obs - P_theo));
mbe = mean(P_obs - P_theo);
R2 = 1 - sum((P_obs - P_theo).^2) / sum((P_obs - mean(P_obs)).^2);

fprintf('\n—— 误差指标（仅白昼）——\n');
fprintf('RMSE: %.4f MW\n', rmse);
fprintf('MAE : %.4f MW\n', mae);
fprintf('MBE : %.4f MW\n', mbe);
fprintf('R²  : %.4f\n', R2);

%% ------------------------ 10. 残差可视化 ------------------------
figure;
plot(T.Time(daylight), P_obs - P_theo, 'b.');
xlabel('时间'); ylabel('残差 (实际 - 理论) MW');
title('实际功率与理论功率的残差图（白昼）');
grid on;

% 10.1 月度残差（绝对误差）条形图
T.Residual = T.Power - T.TheoPower;
monthly_error = varfun(@(x) mean(abs(x)), T, ...
    'GroupingVariables','Month', 'InputVariables','Residual');
figure;
bar(monthly_error.Month, monthly_error.Fun_Residual);
xlabel('月份'); ylabel('平均绝对偏差 (MW)');
title('各月平均残差（|实际 - 理论|）');
grid on;

% 一、季节性偏差归因分析
% 思路推导：
% 目标是解释“理论与实际功率在不同月份差距为何不同”；
% 
% 使用残差（实际 - 理论）为分析对象；
% 
% 计算每月的温度、湿度、气压等均值，查看与月残差的关系；
% 
% 可使用散点图或回归判断关键影响因子。
% 1.1 添加残差列
T.Residual = T.Power - T.TheoPower;

% 1.2 统计每月平均温度、湿度、压力、残差
monthly_env = groupsummary(T, 'Month', {'mean'}, {'Temp','Humidity','Pressure','Residual'});

% 1.3 绘图：残差 vs 月均环境因子
figure;
subplot(3,1,1);
plot(monthly_env.Month, monthly_env.mean_Temp, 'ro-', 'LineWidth', 1.5); hold on;
yyaxis right;
plot(monthly_env.Month, monthly_env.mean_Residual, 'k--', 'LineWidth', 1.5);
xlabel('月份'); ylabel('温度 / 残差');
legend('平均温度','月平均残差');
title('温度与月度残差关系');

subplot(3,1,2);
plot(monthly_env.Month, monthly_env.mean_Humidity, 'bo-', 'LineWidth', 1.5); hold on;
yyaxis right;
plot(monthly_env.Month, monthly_env.mean_Residual, 'k--', 'LineWidth', 1.5);
xlabel('月份'); ylabel('湿度 / 残差');
legend('平均湿度','月平均残差');
title('湿度与月度残差关系');

subplot(3,1,3);
plot(monthly_env.Month, monthly_env.mean_Pressure, 'go-', 'LineWidth', 1.5); hold on;
yyaxis right;
plot(monthly_env.Month, monthly_env.mean_Residual, 'k--', 'LineWidth', 1.5);
xlabel('月份'); ylabel('气压 / 残差');
legend('平均气压','月平均残差');
title('气压与月度残差关系');

% 二、天气条件效率对比
%思路推导：
%根据湿度与GHI划分样本类型：
% 2.1 计算瞬时效率（白昼段）
T.Efficiency = T.Power ./ T.TheoPower;
T = T(T.GHI > 50 & isfinite(T.Efficiency), :);  % 白天筛选 + 有效值

% 2.2 添加天气分类标签
T.WeatherType = strings(height(T),1);
T.WeatherType(T.Humidity > 70) = "高湿";
T.WeatherType(T.Humidity < 40) = "低湿";
T.WeatherType(T.GHI < 300) = "阴天";
T.WeatherType(T.GHI > 800) = "晴天";
T.WeatherType(T.WeatherType == "") = "中间态";

% 2.3 分组统计效率
eff_stats = groupsummary(T, "WeatherType", "mean", "Efficiency");

% 2.4 绘图
figure;
bar(categorical(eff_stats.WeatherType), eff_stats.mean_Efficiency);
ylabel('平均效率（P_{actual} / P_{theo}）');
title('不同天气条件下的发电效率对比');
grid on;

% 三、功率损失解释体系
% 思路推导：
% 目标是将功率损失（理论 - 实际）拆解为各物理因子引起的衰减；
% 
% 使用“只移除单一修正项”再计算理论功率，观察变化；
% 3.1 去掉温度效率影响
% 3.1 去掉温度效率影响（使用恒定效率）
T.TheoPower_noTemp = eta_ref .* G_eff_corr .* A / 1e6;

% 3.2 Tatm = 1（无大气透射衰减）
G_eff_nocorr = G_eff;  % 未经过Tatm修正的有效辐照度
T.TheoPower_noTatm = eta .* G_eff_nocorr .* A / 1e6;

% 3.3 cos(theta_i) = 1（假设辐照始终垂直入射）
G_eff_flat = T.DNI + T.DHI .* (1 + cosd(beta))/2 + rho_g * T.GHI .* (1 - cosd(beta))/2;
G_eff_flat = Tatm .* G_eff_flat;
T.TheoPower_noAngle = eta .* G_eff_flat .* A / 1e6;

%图1：实际 vs 理论 功率（增强版）
% 方法1：按日平均降采样
T.Date = dateshift(T.Time, 'start', 'day');
daily = varfun(@mean, T, 'GroupingVariables','Date', 'InputVariables',{'Power','TheoPower'});

figure;
plot(daily.Date, daily.mean_Power, 'r-', 'LineWidth', 1); hold on;
plot(daily.Date, daily.mean_TheoPower, 'k--', 'LineWidth', 1);
xlabel('日期'); ylabel('日均功率 (MW)');
legend('实际功率（日均）', '理论功率（日均）');
title('图1增强：按日聚合展示发电趋势');
grid on;

% 方法2：热力图展示年度日内功率模式
T.Hour = hour(T.Time) + minute(T.Time)/60;
T.DayOfYear = day(T.Time, 'dayofyear');
G = T.Power;
Z = accumarray([T.DayOfYear, round(T.Hour*4)+1], G, [], @mean, NaN);

figure;
imagesc((0:0.25:23.75), 1:366, Z);
axis xy; colorbar;
xlabel('一天中的小时'); ylabel('年中日序');
title('图1替代：年度发电热力图（实际功率）');

%图2：月平均对比图（增强版）
% 方法1：添加误差条（标准差）
monthly_std = varfun(@std, T, 'GroupingVariables','Month', ...
    'InputVariables', {'Power','TheoPower'});

figure;
errorbar(monthly.Month, monthly.mean_Power, monthly_std.std_Power, 'r', 'LineWidth', 1.5); hold on;
errorbar(monthly.Month, monthly.mean_TheoPower, monthly_std.std_TheoPower, 'k--', 'LineWidth', 1.5);
legend('实际功率','理论功率');
xlabel('月份'); ylabel('功率 (MW)');
title('图2增强：月均功率+波动（误差条）');
grid on;

% 方法2：堆叠面积图
figure;
area(monthly.Month, [monthly.mean_TheoPower, monthly.mean_Power - monthly.mean_TheoPower], 'LineStyle', 'none');
legend('理论功率','偏差部分（实际-理论）');
xlabel('月份'); ylabel('功率 (MW)');
title('图2替代：功率差值堆叠图');

%图3：日内平均曲线（增强版）
profile_std = varfun(@std, T, 'GroupingVariables','HourMinute', ...
    'InputVariables', {'Power','TheoPower'});

% 方法1：误差带
figure;
fill([profile.HourMinute; flipud(profile.HourMinute)], ...
     [profile.mean_Power - profile_std.std_Power; flipud(profile.mean_Power + profile_std.std_Power)], ...
     'r', 'FaceAlpha', 0.2, 'EdgeColor','none'); hold on;
plot(profile.HourMinute, profile.mean_Power, 'r-', 'LineWidth', 1.5);
plot(profile.HourMinute, profile.mean_TheoPower, 'k--', 'LineWidth', 1.5);
xlabel('时间'); ylabel('平均功率 (MW)');
legend('误差范围','实际功率','理论功率');
title('图3增强：日内平均功率+误差带');
grid on;

% 方法2：极坐标图（展现周期性）
theta = 2*pi * hours(profile.HourMinute) / 24;
figure;
polarplot(theta, profile.mean_Power, 'r-', theta, profile.mean_TheoPower, 'k--', 'LineWidth', 1.5);
title('图3替代：极坐标形式的日内变化');

%图4：残差图（增强版）
% 方法1：2D热力图
edges_time = linspace(datenum(min(T.Time)), datenum(max(T.Time)), 200);
edges_res = linspace(-100, 100, 100);
[counts, Xedges, Yedges] = histcounts2(datenum(T.Time(daylight)), P_obs - P_theo, edges_time, edges_res);

figure;
imagesc(datetime(Xedges(1:end-1), 'ConvertFrom','datenum'), Yedges, counts');
axis xy; colorbar;
xlabel('时间'); ylabel('残差 (MW)');
title('图4增强：残差时间热图');

% 方法2：月残差箱线图
figure;
boxplot(T.Residual(daylight), month(T.Time(daylight)));
xlabel('月份'); ylabel('残差 (MW)');
title('图4替代：各月残差分布（箱型图）');
grid on;

%图5：天气条件效率图（增强）
% 小提琴图替代
categories = unique(T.WeatherType);
eff_cell = arrayfun(@(c) T.Efficiency(T.WeatherType == c), categories, 'UniformOutput', false);
figure;
violinplot(eff_cell, categories);
ylabel('效率'); title('图5增强：天气条件下发电效率分布（小提琴图）');

toc;
