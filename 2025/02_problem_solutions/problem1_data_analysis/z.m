%% ------------------------ 1. 读取与预处理数据 ------------------------
clear; clc; tic;
scriptDir = fileparts(mfilename('fullpath'));
projectRoot = fileparts(fileparts(fileparts(scriptDir)));
addpath(fullfile(projectRoot, '_shared', 'matlab'));
filename = resolve_project_input('station00.csv', scriptDir);
T = readtable(filename);

% 重命名变量
T.Properties.VariableNames = {'Time','GHI','DNI','Temp','Humidity','NWP_WindSpeed','NWP_WindDir','NWP_Pressure',...
                              'TotalIrradiance','DHI','LMD_Temp','Pressure','LMD_WindDir','LMD_WindSpeed','Power'};
T.Time = datetime(T.Time, 'InputFormat', 'yyyy-MM-dd HH:mm:ss');

%% ------------------------ 2. 固定参数设置 ------------------------
A = 36666.667; beta = 31.17; phi_p = 180; rho_g = 0.2;
eta_ref = 0.18; gamma = 0.0035; kappa = 0.02;
tau_a = 0.15; U_o = 0.3;

%% ------------------------ 3. 太阳位置与时间修正 ------------------------
latitude = 31.1708218;  longitude = 115.0159244;
d = day(T.Time,'dayofyear');
h = hour(T.Time) + minute(T.Time)/60 + second(T.Time)/3600;
lat = deg2rad(latitude);  lon = longitude;

B = 2*pi*(d - 81)/364;
EoT = 9.87*sin(2*B) - 7.53*cos(B) - 1.5*sin(B);
LSTM = 15 * round(lon/15);
TC = 4*(lon - LSTM) + EoT; LST = h + TC/60;

HRA = deg2rad(15*(LST - 12));
delta = deg2rad(23.45)*sin(2*pi*(284+d)/365);

sin_alpha = sin(lat).*sin(delta) + cos(lat).*cos(delta).*cos(HRA);
alpha = asin(sin_alpha); zenith = rad2deg(pi/2 - alpha);

cos_Az = (sin(delta) - sin(lat).*sin_alpha) ./ (cos(lat).*cos(alpha));
cos_Az = min(max(cos_Az, -1), 1);
Az_rad = acos(cos_Az);
phi_s = rad2deg(Az_rad);
phi_s(h > 12) = 360 - phi_s(h > 12);
theta_z = zenith;

%% ------------------------ 4. 入射角与辐照度计算 ------------------------
cos_theta_i = cosd(theta_z) .* cosd(beta) + ...
              sind(theta_z) .* sind(beta) .* cosd(phi_s - phi_p);
cos_theta_i = max(cos_theta_i, 0.05);

%% ------------------------ 5. 大气透射率计算 ------------------------
m = 1 ./ (cosd(theta_z) + 0.50572 .* (96.07995 - theta_z).^(-1.6364));
m(isnan(m) | isinf(m)) = 10;

Tr = exp(-0.0903 .* (T.Pressure ./ 1013.25).^0.84 ./ (1 + cosd(theta_z)).^1.01);
Ta = exp(-tau_a .* (0.6777 + 0.1464*tau_a - 0.00626*tau_a.^2) .* m);
To = 1 - 0.011 .* (U_o .* m) ./ (1 + 0.006 .* (U_o .* m).^1.5);
Uw = 0.1 .* T.Humidity .* exp(0.07 .* T.Temp);
Tw = 1 - 0.077 .* (Uw .* m).^0.3;
Tg = exp(-0.0117 .* m.^0.3139);
Tatm = Tr .* Ta .* To .* Tw .* Tg;
Tatm = 0.8;

%% ------------------------ 6. 有效辐照度与功率计算 ------------------------
G_eff = T.DNI .* cos_theta_i + ...
        T.DHI .* (1 + cosd(beta)) / 2 + ...
        rho_g .* T.GHI .* (1 - cosd(beta)) / 2;
G_eff_corr = Tatm .* G_eff;
eta = 0.22;
T.TheoPower = eta .* G_eff_corr .* A / 1e6;

%% ------------------------ 7. 数据清洗 ------------------------
T.Power = real(double(T.Power));
T.TheoPower = real(double(T.TheoPower));
validIdx = isfinite(T.Power) & isfinite(T.TheoPower);
daylight = T.GHI > 0;

%% ------------------------ 8. 基本图形分析 ------------------------
% 日序图
figure;
plot(T.Time(validIdx), T.Power(validIdx), 'r-'); hold on;
plot(T.Time(validIdx), T.TheoPower(validIdx), 'k--');
legend('实际','理论'); xlabel('时间'); ylabel('功率'); grid on; title('功率时序对比');

% 月均图
T.Month = month(T.Time);
monthly = varfun(@mean, T, 'GroupingVariables','Month', 'InputVariables', {'Power','TheoPower'});
figure;
bar(monthly.Month, [monthly.mean_Power, monthly.mean_TheoPower]);
legend('实际','理论'); xlabel('月份'); ylabel('平均功率'); grid on;

% 日内曲线图
T.HourMinute = timeofday(T.Time);
profile = varfun(@mean, T, 'GroupingVariables','HourMinute', 'InputVariables', {'Power','TheoPower'});
figure;
plot(profile.HourMinute, profile.mean_Power, 'r-', 'LineWidth',1.5); hold on;
plot(profile.HourMinute, profile.mean_TheoPower, 'k--', 'LineWidth',1.5);
legend('实际','理论'); xlabel('时间'); ylabel('平均功率'); grid on; title('日内功率平均曲线');

%% ------------------------ 9. 误差指标 ------------------------
P_obs = T.Power(daylight);
P_theo = T.TheoPower(daylight);
rmse = sqrt(mean((P_obs - P_theo).^2));
mae = mean(abs(P_obs - P_theo));
mbe = mean(P_obs - P_theo);
R2 = 1 - sum((P_obs - P_theo).^2) / sum((P_obs - mean(P_obs)).^2);

fprintf('\n—— 误差指标（白昼）——\n');
fprintf('RMSE: %.4f MW\n', rmse);
fprintf('MAE : %.4f MW\n', mae);
fprintf('MBE : %.4f MW\n', mbe);
fprintf('R²  : %.4f\n', R2);

%% ------------------------ 10. 残差分析与扩展图形 ------------------------
T.Residual = T.Power - T.TheoPower;

% 极坐标图（日内周期性）
theta = 2*pi * hours(T.HourMinute) / 24;
avgP = profile.mean_Power;
avgTheo = profile.mean_TheoPower;
figure; polarplot(theta, avgP, 'r-', theta, avgTheo, 'k--', 'LineWidth', 1.5);
title('极坐标：日内功率周期性');

% 热力图：年内日内功率模式
T.Hour = hour(T.Time) + minute(T.Time)/60;
T.DayOfYear = day(T.Time, 'dayofyear');
Z = accumarray([T.DayOfYear, round(T.Hour*4)+1], T.Power, [366, 96], @mean, NaN);

figure;
imagesc(0:0.25:23.75, 1:366, Z);  % X: 96列, Y
 axis xy; colorbar;
xlabel('小时'); ylabel('年中日序'); title('热力图：年内功率模式');

% 小提琴图（天气条件下效率）
T.Efficiency = T.Power ./ T.TheoPower;
T.WeatherType = strings(height(T),1);
T.WeatherType(T.Humidity > 70) = "高湿";
T.WeatherType(T.Humidity < 40) = "低湿";
T.WeatherType(T.GHI < 300) = "阴天";
T.WeatherType(T.GHI > 800) = "晴天";
T.WeatherType(T.WeatherType == "") = "中间态";

cats = unique(T.WeatherType);
data = cellfun(@(c) T.Efficiency(T.WeatherType == c), cellstr(cats), 'UniformOutput', false);
figure;
violinplot(data, cats);
ylabel('效率'); title('小提琴图：天气条件下发电效率');
