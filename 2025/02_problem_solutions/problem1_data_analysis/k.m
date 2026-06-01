clear; clc; tic;

%% 1. 读取与预处理数据
scriptDir = fileparts(mfilename('fullpath'));
projectRoot = fileparts(fileparts(fileparts(scriptDir)));
addpath(fullfile(projectRoot, '_shared', 'matlab'));
filename = resolve_project_input('Solar station site 5 (Nominal capacity-110MW).xlsx', scriptDir);
T = readtable(filename, 'VariableNamingRule', 'preserve');
T.Properties.VariableNames = {'Time','TotalIrradiance','DNI','GHI','Temp','Pressure','Humidity','Power'};
T.Time = datetime(T.Time, 'InputFormat', 'yyyy-MM-dd HH:mm:ss');

%% 2. 固定参数
A = 611111.11;
beta = 31.17;
phi_p = 180;
rho_g = 0.2;
eta_ref = 0.18;
gamma = 0.0035;
kappa = 0.02;
tau_a = 0.15;
U_o = 0.3;

%% 3. 地理与太阳位置计算
latitude = 31.1708218; longitude = 115.0159244;
d = day(T.Time,'dayofyear');
h = hour(T.Time) + minute(T.Time)/60 + second(T.Time)/3600;

lat = deg2rad(latitude);
B = 2*pi*(d - 81)/364;
EoT = 9.87*sin(2*B) - 7.53*cos(B) - 1.5*sin(B);
LSTM = 15 * round(longitude/15);
TC = 4*(longitude - LSTM) + EoT;
LST = h + TC/60;

HRA = deg2rad(15*(LST - 12));
delta = deg2rad(23.45)*sin(2*pi*(284+d)/365);
sin_alpha = sin(lat).*sin(delta) + cos(lat).*cos(delta).*cos(HRA);
alpha = asin(sin_alpha);
zenith = rad2deg(pi/2 - alpha);
cos_Az = (sin(delta) - sin(lat).*sin_alpha) ./ (cos(lat).*cos(alpha));
cos_Az = min(max(cos_Az, -1), 1);
Az_rad = acos(cos_Az);
phi_s = rad2deg(Az_rad);
phi_s(h > 12) = 360 - phi_s(h > 12);

theta_z = zenith;

%% 4. 入射角与辐射分解
cos_theta_i = cosd(theta_z).*cosd(beta) + sind(theta_z).*sind(beta).*cosd(phi_s - phi_p);
cos_theta_i = max(cos_theta_i, 0.05);
T.DHI = T.GHI - T.DNI .* cosd(theta_z);
T.DHI = max(T.DHI, 0);

%% 5. 大气透射率计算
m = 1 ./ (cosd(theta_z) + 0.50572 .* (96.07995 - theta_z).^(-1.6364));
m(isnan(m) | isinf(m)) = 10;
Tr = exp(-0.0903 .* (T.Pressure ./ 1013.25).^0.84 ./ (1 + cosd(theta_z)).^1.01);
Ta = exp(-tau_a .* (0.6777 + 0.1464*tau_a - 0.00626*tau_a.^2) .* m);
To = 1 - 0.011 .* (U_o .* m) ./ (1 + 0.006 .* (U_o .* m).^1.5);
Uw = 0.1 .* T.Humidity .* exp(0.07 .* T.Temp);
Tw = 1 - 0.077 .* (Uw .* m).^0.3;
Tg = exp(-0.0117 .* m.^0.3139);
Tatm = Tr .* Ta .* To .* Tw .* Tg;

%% 6. 有效辐照度与效率修正
G_eff = T.DNI .* cos_theta_i + ...
        T.DHI .* (1 + cosd(beta)) / 2 + ...
        rho_g .* T.GHI .* (1 - cosd(beta)) / 2;

Tatm = 0.85;
G_eff_corr = Tatm .* G_eff;
eta = eta_ref .* (1 - gamma .* (T.Temp + kappa .* T.GHI - 25));
eta = 0.22;
T.TheoPower = eta .* G_eff_corr .* A / 1e6;

%% 7. 数据清洗与有效性
T.Power = real(double(T.Power));
T.TheoPower = real(double(T.TheoPower));
validIdx = isfinite(T.Power) & isfinite(T.TheoPower);
daylight = T.GHI > 20;

%% 8. 基础图像分析（增强版）
T.Date = dateshift(T.Time, 'start', 'day');
daily = varfun(@mean, T, 'GroupingVariables','Date', 'InputVariables',{'Power','TheoPower'});
figure; plot(daily.Date, daily.mean_Power, 'r-', daily.Date, daily.mean_TheoPower, 'k--');
xlabel('日期'); ylabel('功率 (MW)'); legend('实际', '理论'); title('日均功率对比'); grid on;

T.Month = month(T.Time);
monthly = varfun(@mean, T, 'GroupingVariables','Month', 'InputVariables', {'Power','TheoPower'});
monthly_std = varfun(@std, T, 'GroupingVariables','Month', 'InputVariables', {'Power','TheoPower'});
figure;
errorbar(monthly.Month, monthly.mean_Power, monthly_std.std_Power, 'r'); hold on;
errorbar(monthly.Month, monthly.mean_TheoPower, monthly_std.std_TheoPower, 'k--');
xlabel('月份'); ylabel('功率'); title('月均功率+波动'); legend('实际','理论'); grid on;

T.HourMinute = timeofday(T.Time);
profile = varfun(@mean, T, 'GroupingVariables','HourMinute', 'InputVariables', {'Power','TheoPower'});
profile_std = varfun(@std, T, 'GroupingVariables','HourMinute', 'InputVariables', {'Power','TheoPower'});
figure;
fill([profile.HourMinute; flipud(profile.HourMinute)], ...
     [profile.mean_Power - profile_std.std_Power; flipud(profile.mean_Power + profile_std.std_Power)], ...
     'r', 'FaceAlpha', 0.2, 'EdgeColor','none'); hold on;
plot(profile.HourMinute, profile.mean_Power, 'r-');
plot(profile.HourMinute, profile.mean_TheoPower, 'k--');
xlabel('时间'); ylabel('平均功率 (MW)'); legend('误差带','实际','理论'); title('日内平均功率变化'); grid on;

%% 9. 偏差分析
P_obs = T.Power(daylight);
P_theo = T.TheoPower(daylight);
rmse = sqrt(mean((P_obs - P_theo).^2));
mae = mean(abs(P_obs - P_theo));
mbe = mean(P_obs - P_theo);
R2 = 1 - sum((P_obs - P_theo).^2) / sum((P_obs - mean(P_obs)).^2);

fprintf('\n—— 误差指标（仅白昼）——\n');
fprintf('RMSE: %.4f MW\nMAE : %.4f MW\nMBE : %.4f MW\nR²  : %.4f\n', rmse, mae, mbe, R2);

%% 10. 残差可视化
T.Residual = T.Power - T.TheoPower;
figure; plot(T.Time(daylight), T.Residual(daylight), 'b.');
xlabel('时间'); ylabel('残差'); title('残差时序图（白昼）'); grid on;

monthly_error = varfun(@(x) mean(abs(x)), T, 'GroupingVariables','Month', 'InputVariables','Residual');
figure; bar(monthly_error.Month, monthly_error.Fun_Residual);
xlabel('月份'); ylabel('平均残差'); title('月平均残差（绝对值）'); grid on;

figure; boxplot(T.Residual(daylight), month(T.Time(daylight)));
xlabel('月份'); ylabel('残差 (MW)'); title('月度残差箱型图'); grid on;

%% 11. 环境因子与残差关系
monthly_env = groupsummary(T, 'Month', {'mean'}, {'Temp','Humidity','Pressure','Residual'});
figure;
subplot(3,1,1);
plot(monthly_env.Month, monthly_env.mean_Temp, 'ro-'); yyaxis right;
plot(monthly_env.Month, monthly_env.mean_Residual, 'k--'); title('温度与残差');
subplot(3,1,2);
plot(monthly_env.Month, monthly_env.mean_Humidity, 'bo-'); yyaxis right;
plot(monthly_env.Month, monthly_env.mean_Residual, 'k--'); title('湿度与残差');
subplot(3,1,3);
plot(monthly_env.Month, monthly_env.mean_Pressure, 'go-'); yyaxis right;
plot(monthly_env.Month, monthly_env.mean_Residual, 'k--'); title('气压与残差');

%% 12. 天气类型与效率对比
T.Efficiency = T.Power ./ T.TheoPower;
T = T(T.GHI > 50 & isfinite(T.Efficiency), :);
T.WeatherType = strings(height(T),1);
T.WeatherType(T.Humidity > 70) = "高湿";
T.WeatherType(T.Humidity < 40) = "低湿";
T.WeatherType(T.GHI < 300) = "阴天";
T.WeatherType(T.GHI > 800) = "晴天";
T.WeatherType(T.WeatherType == "") = "中间态";

eff_stats = groupsummary(T, "WeatherType", "mean", "Efficiency");
figure; bar(categorical(eff_stats.WeatherType), eff_stats.mean_Efficiency);
ylabel('效率'); title('不同天气条件效率对比'); grid on;

%%
% 日均功率计算
T.Date = dateshift(T.Time, 'start', 'day');
daily = varfun(@mean, T, 'GroupingVariables','Date', ...
    'InputVariables', {'Power','TheoPower'});

% 偏差
bias = daily.mean_Power - daily.mean_TheoPower;
bias_pos = max(bias, 0);  % 正偏差（超发）
bias_neg = min(bias, 0);  % 负偏差（欠发）

% 创建图形窗口
figure('Color','w');
hold on;

% 设置颜色
color_theo = [0.2 0.6 1];      % 蓝色，理论
color_pos  = [0.3 0.8 0.4];    % 绿色，正偏差
color_neg  = [1 0.4 0.3];      % 红色，负偏差

% 绘图
area(daily.Date, daily.mean_TheoPower, 'FaceColor', color_theo, ...
    'EdgeColor','none', 'FaceAlpha', 0.3, 'DisplayName','理论功率');

area(daily.Date, bias_pos, 'FaceColor', color_pos, ...
    'EdgeColor','none', 'FaceAlpha', 0.6, 'DisplayName','正偏差（超发）');

area(daily.Date, bias_neg, 'FaceColor', color_neg, ...
    'EdgeColor','none', 'FaceAlpha', 0.6, 'DisplayName','负偏差（欠发）');

% 格式设置
xlabel('日期', 'FontName', 'Microsoft YaHei', 'FontSize', 12);
ylabel('功率 (MW)', 'FontName', 'Microsoft YaHei', 'FontSize', 12);
title('日均功率及其偏差（正负分离）', 'FontWeight','bold', ...
    'FontSize', 13, 'FontName', 'Microsoft YaHei');
legend('Location','northeast', 'FontSize', 10, 'Box','off');

grid on;
set(gca, 'FontName','Microsoft YaHei', 'FontSize', 11);


toc;
