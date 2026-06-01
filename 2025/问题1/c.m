clear; clc; tic
%% === 数据读取 ===
filename = 'Solar station site 5 (Nominal capacity-110MW).xlsx';
T = readtable(filename);
% 重命名列（清理空格与统一名称）
T.Properties.VariableNames = {'Time','TotalIrradiance','DNI','GHI','Temp','Pressure','Humidity','Power'};
T.Time = datetime(T.Time, 'InputFormat', 'yyyy-MM-dd HH:mm:ss');

%% === 参数设置 ===
A = 517000;           % 面板面积（110MW / 0.213kW/m² ≈ 517,000 m²）
beta = 31.17;         % 面板倾角（≈纬度）
phi_p = 180;          % 面板朝向（正南）
rho_g = 0.2;          % 地面反射率
eta_ref = 0.18;       % 标准效率
gamma = 0.0045;       % 温度效率下降系数
kappa = 0.03;         % 温升系数
tau_a = 0.15;         % 气溶胶AOD
U_o = 0.3;            % 臭氧柱厚（cm）

%% === 太阳角度计算 ===
d = day(T.Time,'dayofyear');
h = hour(T.Time) + minute(T.Time)/60 + second(T.Time)/3600;
lat = deg2rad(31.1708218); lon = 115.0159244;

B = 2*pi*(d - 81)/364;
EoT = 9.87*sin(2*B) - 7.53*cos(B) - 1.5*sin(B);
LSTM = 15 * round(lon/15);
TC = 4*(lon - LSTM) + EoT;
LST = h + TC/60;

HRA = deg2rad(15*(LST - 12));
delta = deg2rad(23.45)*sin(2*pi*(284+d)/365);
sin_alpha = sin(lat).*sin(delta) + cos(lat).*cos(delta).*cos(HRA);
alpha = asin(sin_alpha);                         % 太阳高度角
theta_z = rad2deg(pi/2 - alpha);                 % 天顶角

cos_Az = (sin(delta) - sin(lat).*sin_alpha) ./ (cos(lat).*cos(alpha));
Az_rad = acos(cos_Az);
phi_s = rad2deg(Az_rad);
phi_s(h > 12) = 360 - phi_s(h > 12);             % 修正下午方向

%% === 入射角与辐射角分量 ===
cos_theta_i = cosd(theta_z) .* cosd(beta) + sind(theta_z) .* sind(beta) .* cosd(phi_s - phi_p);
cos_theta_i = max(cos_theta_i, 0);  % 仅限白天有效

T.DHI = max(T.GHI - T.DNI .* cosd(theta_z), 0);

%% === 大气透射率计算 ===
m = 1 ./ (cosd(theta_z) + 0.50572 .* (96.07995 - theta_z).^(-1.6364));
m(isnan(m)|isinf(m)) = 10;

Tr = exp(-0.0903 .* (T.Pressure ./ 1013.25).^0.84 ./ (1 + cosd(theta_z)).^1.01);
Ta = exp(-tau_a .* (0.6777 + 0.1464*tau_a - 0.00626*tau_a.^2) .* m);
To = 1 - 0.011 .* (U_o .* m) ./ (1 + 0.006 .* (U_o .* m).^1.5);

Uw = 0.1 .* T.Humidity .* exp(0.07 .* T.Temp);
Tw = 1 - 0.077 .* (Uw .* m).^0.3;
Tg = exp(-0.0117 .* m.^0.3139);

Tatm = Tr .* Ta .* To .* Tw .* Tg;

%% === 有效辐照度修正后计算 ===
G_eff = T.DNI .* cos_theta_i + ...
        T.DHI .* (1 + cosd(beta)) / 2 + ...
        rho_g .* T.GHI .* (1 - cosd(beta)) / 2;
G_eff_corr = Tatm .* G_eff;

eta = eta_ref .* (1 - gamma .* (T.Temp + kappa .* T.GHI - 25));
T.TheoPower = eta .* G_eff_corr .* A / 1e6;  % 转为 MW

%% === 清洗绘图数据 ===
validIdx = isfinite(T.TheoPower) & isfinite(T.Power);
time_plot = datetime(T.Time(validIdx));
power_actual = double(T.Power(validIdx));
power_theo = double(T.TheoPower(validIdx));

%% === 图1：时序对比 ===
figure;
plot(time_plot, power_actual, 'r-', 'LineWidth', 1); hold on;
plot(time_plot, power_theo, 'k--', 'LineWidth', 1);
legend('实际功率', '理论功率'); grid on;
xlabel('时间'); ylabel('功率 (MW)');
title('实际功率 vs 理论功率');

%% === 图2：月均季节性对比 ===
T.Month = month(T.Time);
monthly = varfun(@mean, T, 'GroupingVariables','Month', ...
    'InputVariables', {'Power','TheoPower'});

figure;
bar(monthly.Month, [monthly.mean_Power, monthly.mean_TheoPower]);
legend('实际功率', '理论功率');
xlabel('月份'); ylabel('月均功率 (MW)');
title('季节性功率变化对比');
grid on;

%% === 图3：平均日内曲线 ===
T.HourMinute = timeofday(T.Time);
profile = varfun(@mean, T, 'GroupingVariables','HourMinute', ...
    'InputVariables', {'Power','TheoPower'});

figure;
plot(profile.HourMinute, profile.mean_Power, 'r-', 'LineWidth', 1.5); hold on;
plot(profile.HourMinute, profile.mean_TheoPower, 'k--', 'LineWidth', 1.5);
legend('实际功率', '理论功率');
xlabel('一天中的时间'); ylabel('平均功率 (MW)');
title('日内平均功率波动');
grid on;

toc
