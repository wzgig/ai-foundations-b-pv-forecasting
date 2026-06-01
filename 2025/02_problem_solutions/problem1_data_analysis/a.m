clear,clc,tic
%% 读取数据
filename = 'Solar station site 4 (Nominal capacity-130MW).xlsx';
T = readtable(filename);
T.Properties.VariableNames = {'Time','TotalIrradiance','DNI','GHI','Temp','Pressure','Humidity','Power'};
T.Time = datetime(T.Time, 'InputFormat', 'yyyy-MM-dd HH:mm:ss');

%% 固定参数设置
A = 611111.11;         % 面板面积，单位 m²
beta = 31.17;          % 面板倾角（设为纬度）
phi_p = 180;           % 面板朝向（正南）
rho_g = 0.2;           % 地面反射率
eta_ref = 0.18;        % 光伏组件参考效率
gamma = 0.0045;        % 温度修正系数
kappa = 0.03;          % 温升系数
tau_a = 0.15;          % 气溶胶光学深度
U_o = 0.3;             % 臭氧柱厚度（单位 cm）

%% 计算太阳高度角与方位角（用 MATLAB solarPosition）
latitude = 31.1708218;
longitude = 115.0159244;
[~, zenith, azimuth] = solarPosition(T.Time, latitude, longitude); % 天顶角（度）与方位角

theta_z = zenith;                 % 天顶角
phi_s = azimuth;                 % 太阳方位角

%% 入射角计算
cos_theta_i = cosd(theta_z) .* cosd(beta) + sind(theta_z) .* sind(beta) .* cosd(phi_s - phi_p);
cos_theta_i = max(cos_theta_i, 0);  % 防止日落后为负

%% 漫射辐射 DHI
T.DHI = T.GHI - T.DNI .* cosd(theta_z);
T.DHI = max(T.DHI, 0);  % 确保非负

%% 空气质量数（Air Mass）
m = 1 ./ (cosd(theta_z) + 0.50572 .* (96.07995 - theta_z).^(-1.6364));
m(isnan(m)|isinf(m)) = 10;

%% 各大气透射率项计算
Tr = exp(-0.0903 .* (T.Pressure ./ 1013.25).^0.84 ./ (1 + cosd(theta_z)).^1.01);
Ta = exp(-tau_a .* (0.6777 + 0.1464*tau_a - 0.00626*tau_a.^2) .* m);
To = 1 - 0.011 .* (U_o .* m) ./ (1 + 0.006 .* (U_o .* m).^1.5);

% 水汽估算（单位 cm）
Uw = 0.1 .* T.Humidity .* exp(0.07 .* T.Temp);
Tw = 1 - 0.077 .* (Uw .* m).^0.3;
Tg = exp(-0.0117 .* m.^0.3139);

Tatm = Tr .* Ta .* To .* Tw .* Tg;

%% 有效辐照度计算（含角度 + 地面反射）
G_eff = T.DNI .* cos_theta_i + ...
        T.DHI .* (1 + cosd(beta)) / 2 + ...
        rho_g .* T.GHI .* (1 - cosd(beta)) / 2;

% 修正后的有效辐照
G_eff_corr = Tatm .* G_eff;

%% 温度效率修正
eta = eta_ref .* (1 - gamma .* (T.Temp + kappa .* T.GHI - 25));

%% 计算理论功率
T.TheoPower = eta .* G_eff_corr .* A / 1e6;  % 转为 MW

%% 可视化：时序对比图
figure;
plot(T.Time, T.Power, 'r-', 'LineWidth', 1); hold on;
plot(T.Time, T.TheoPower, 'k--', 'LineWidth', 1);
legend('实际功率', '理论功率');
xlabel('时间'); ylabel('功率 (MW)');
title('实际功率 vs 理论功率');
grid on;

%% 可视化：月平均功率比较（季节性）
T.Month = month(T.Time);
monthly = varfun(@mean, T, 'GroupingVariables','Month', ...
    'InputVariables', {'Power','TheoPower'});

figure;
bar(monthly.Month, [monthly.mean_Power, monthly.mean_TheoPower]);
legend('实际功率', '理论功率');
xlabel('月份'); ylabel('月均功率 (MW)');
title('季节性波动：实际 vs 理论功率');
grid on;

%% 可视化：平均日内曲线（短周期波动）
T.HourMinute = timeofday(T.Time);
profile = varfun(@mean, T, 'GroupingVariables','HourMinute', ...
    'InputVariables', {'Power','TheoPower'});

figure;
plot(profile.HourMinute, profile.mean_Power, 'r-', 'LineWidth', 1.5); hold on;
plot(profile.HourMinute, profile.mean_TheoPower, 'k--', 'LineWidth', 1.5);
legend('实际功率', '理论功率');
xlabel('一天中的时间'); ylabel('平均功率 (MW)');
title('日内平均功率变化');
grid on;

toc