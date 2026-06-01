clear; clc; tic;  % 清除环境变量与命令窗口，计时器开始

%% 读取数据
filename = 'Solar station site 5 (Nominal capacity-110MW).xlsx';
% 保留原始变量名，避免 MATLAB 自动更改列名
T = readtable(filename, 'VariableNamingRule', 'preserve');  
% 重命名列变量，统一格式
T.Properties.VariableNames = {'Time','TotalIrradiance','DNI','GHI','Temp','Pressure','Humidity','Power'};
% 转换时间字符串为 datetime 类型
T.Time = datetime(T.Time, 'InputFormat', 'yyyy-MM-dd HH:mm:ss');

%% 固定参数设置（组件与模型参数）
A = 611111.11;         % 光伏面板总面积，单位 m²（对应110MW系统）
beta = 31.17;          % 面板倾角，设为当地纬度
phi_p = 180;           % 面板朝向角，180 表示正南
rho_g = 0.2;           % 地表反射率（草地/土地）
eta_ref = 0.18;        % 标准条件下的组件效率
gamma = 0.0035;        % 效率温度衰减系数（每度）
kappa = 0.02;          % 温升系数（表示模块温度高于环境温度的程度）
tau_a = 0.15;          % 气溶胶光学厚度
U_o = 0.3;             % 臭氧柱浓度（cm）

%% 地理信息与时间处理（太阳位置计算所需）
latitude = 31.1708218;
longitude = 115.0159244;

% 提取一年中的第几天和时间（小时）
d = day(T.Time,'dayofyear');  % 年中第几天
h = hour(T.Time) + minute(T.Time)/60 + second(T.Time)/3600;  % UTC小时

lat = deg2rad(latitude);  % 纬度转换为弧度
lon = longitude;

% 计算时间修正项
B = 2*pi*(d - 81)/364;
EoT = 9.87*sin(2*B) - 7.53*cos(B) - 1.5*sin(B);  % 时间方程，单位：分钟
LSTM = 15 * round(lon/15);  % 标准时区子午线
TC = 4*(lon - LSTM) + EoT;  % 时间修正（分钟）
LST = h + TC/60;  % 太阳时（小时）

% 太阳时角 HRA
HRA = deg2rad(15*(LST - 12));

% 太阳赤纬角 δ
delta = deg2rad(23.45)*sin(2*pi*(284+d)/365);

% 太阳高度角 α（单位：弧度）
sin_alpha = sin(lat).*sin(delta) + cos(lat).*cos(delta).*cos(HRA);
alpha = asin(sin_alpha);  
zenith = rad2deg(pi/2 - alpha);  % 天顶角（度）

% 太阳方位角 φ_s
cos_Az = (sin(delta) - sin(lat).*sin_alpha) ./ (cos(lat).*cos(alpha));
cos_Az = min(max(cos_Az, -1), 1);  % 限定在 acos 的定义域
Az_rad = acos(cos_Az);
phi_s = rad2deg(Az_rad);  % 方位角
phi_s(h > 12) = 360 - phi_s(h > 12);  % 下午时需修正

theta_z = zenith;  % 简化变量名：天顶角（度）

%% 入射角与散射辐射计算
% 太阳辐射入射角余弦值（角度修正）
cos_theta_i = cosd(theta_z) .* cosd(beta) + ...
              sind(theta_z) .* sind(beta) .* cosd(phi_s - phi_p);
cos_theta_i = max(cos_theta_i, 0.05);  % 最小值设置，避免0导致无计算值

% 漫射辐射（由总水平辐射与直接辐射反算）
T.DHI = T.GHI - T.DNI .* cosd(theta_z);
T.DHI = max(T.DHI, 0);  % 负值修正为0

%% 空气质量与大气透射率计算
m = 1 ./ (cosd(theta_z) + 0.50572 .* (96.07995 - theta_z).^(-1.6364));  % 空气质量数 AM
m(isnan(m) | isinf(m)) = 10;  % 修复无效值

% 多种大气衰减模型
Tr = exp(-0.0903 .* (T.Pressure ./ 1013.25).^0.84 ./ (1 + cosd(theta_z)).^1.01);  % 瑞利散射
Ta = exp(-tau_a .* (0.6777 + 0.1464*tau_a - 0.00626*tau_a.^2) .* m);              % 气溶胶
To = 1 - 0.011 .* (U_o .* m) ./ (1 + 0.006 .* (U_o .* m).^1.5);                    % 臭氧
Uw = 0.1 .* T.Humidity .* exp(0.07 .* T.Temp);                                     % 水汽含量估计
Tw = 1 - 0.077 .* (Uw .* m).^0.3;                                                  % 水汽吸收
Tg = exp(-0.0117 .* m.^0.3139);                                                    % 气体吸收
Tatm = Tr .* Ta .* To .* Tw .* Tg;  % 总大气透射率

%% 有效辐照度与温度效率修正
% 三部分叠加：直接、漫射、地面反射
G_eff = T.DNI .* cos_theta_i + ...
        T.DHI .* (1 + cosd(beta)) / 2 + ...
        rho_g .* T.GHI .* (1 - cosd(beta)) / 2;

% 透射率修正后的有效辐照度
Tatm = 0.85;
G_eff_corr = Tatm .* G_eff;

% 组件温度效率修正模型
eta = eta_ref .* (1 - gamma .* (T.Temp + kappa .* T.GHI - 25));

% 理论发电功率（单位 MW）
eta = 0.22;
T.TheoPower = eta .* G_eff_corr .* A / 1e6;

%% 数据清洗：移除非数值项
T.Power = real(double(T.Power));
T.TheoPower = real(double(T.TheoPower));
validIdx = isfinite(T.Power) & isfinite(T.TheoPower);  % 有效索引筛选

%% 可视化：时间序列对比图
figure;
plot(T.Time(validIdx), T.Power(validIdx), 'r-', 'LineWidth', 1); hold on;
plot(T.Time(validIdx), T.TheoPower(validIdx), 'k--', 'LineWidth', 1);
legend('实际功率', '理论功率');
xlabel('时间'); ylabel('功率 (MW)');
title('实际功率 vs 理论功率');
grid on;

%% 可视化：月均功率图（季节性变化）
T.Month = month(T.Time);  % 提取月份
monthly = varfun(@mean, T, 'GroupingVariables','Month', ...
    'InputVariables', {'Power','TheoPower'});

figure;
bar(monthly.Month, [monthly.mean_Power, monthly.mean_TheoPower]);
legend('实际功率', '理论功率');
xlabel('月份'); ylabel('月均功率 (MW)');
title('季节性波动：实际 vs 理论功率');
grid on;

%% 可视化：日内平均功率曲线（分析日变化规律）
T.HourMinute = timeofday(T.Time);  % 提取时分信息
profile = varfun(@mean, T, 'GroupingVariables','HourMinute', ...
    'InputVariables', {'Power','TheoPower'});

figure;
plot(profile.HourMinute, profile.mean_Power, 'r-', 'LineWidth', 1.5); hold on;
plot(profile.HourMinute, profile.mean_TheoPower, 'k--', 'LineWidth', 1.5);
legend('实际功率', '理论功率');
xlabel('一天中的时间'); ylabel('平均功率 (MW)');
title('日内平均功率变化');
grid on;

toc;  % 显示运行时间
