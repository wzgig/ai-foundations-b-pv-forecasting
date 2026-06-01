clear,clc,tic
%% 读取数据
scriptDir = fileparts(mfilename('fullpath'));
projectRoot = fileparts(fileparts(fileparts(scriptDir)));
addpath(fullfile(projectRoot, '_shared', 'matlab'));
filename = resolve_project_input( ...
    'Solar station site 4 (Nominal capacity-130MW).xlsx', scriptDir, ...
    {'Solar station site 5 (Nominal capacity-110MW).xlsx'});
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
%% 使用简化太阳天顶角与方位角模型计算
% 提取时间参数
d = day(T.Time,'dayofyear');  % 一年中的第几天
h = hour(T.Time) + minute(T.Time)/60 + second(T.Time)/3600; % 小时数（UTC+0）

% 地理信息
lat = deg2rad(31.1708218);  % 纬度，单位弧度
lon = 115.0159244;          % 经度

% 时间修正因子
B = 2*pi*(d - 81)/364;
EoT = 9.87*sin(2*B) - 7.53*cos(B) - 1.5*sin(B);  % Equation of Time (min)
LSTM = 15 * round(lon/15);                      % Local Standard Time Meridian
TC = 4*(lon - LSTM) + EoT;                      % Time Correction (min)
LST = h + TC/60;                                % Local Solar Time (h)

% 时角 (Hour Angle)
HRA = deg2rad(15*(LST - 12));   % 弧度

% 太阳赤纬角 δ
delta = deg2rad(23.45)*sin(2*pi*(284+d)/365);

% 太阳高度角 α
sin_alpha = sin(lat).*sin(delta) + cos(lat).*cos(delta).*cos(HRA);
alpha = asin(sin_alpha);    % 太阳高度角（弧度）
zenith = rad2deg(pi/2 - alpha);  % 天顶角（度）

% 太阳方位角 φ_s（从北顺时针）
cos_Az = (sin(delta) - sin(lat).*sin_alpha) ./ (cos(lat).*cos(alpha));
Az_rad = acos(cos_Az);
phi_s = rad2deg(Az_rad);
phi_s(h > 12) = 360 - phi_s(h > 12);  % 下午需修正方向
theta_z = zenith;                 % 天顶角
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
