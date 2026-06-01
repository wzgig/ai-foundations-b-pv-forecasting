# -*- coding: utf-8 -*-
"""
Created on 2025/5/24 10:05

@author: Prince
"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
from math import radians, cos, sin, acos, exp
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.integrate import odeint  # 使用odeint替代ode45
from sklearn.preprocessing import MinMaxScaler
from matplotlib import rcParams

rcParams['font.family'] = 'SimHei'  # 或者其他中文字体，如 'Microsoft YaHei'
rcParams['axes.unicode_minus'] = False  # 解决负号显示问题

# === 基本参数设定 === #
LAT = 31.1708218      # 纬度
LON = 115.0159244     # 经度
BETA = 31.17          # 面板倾角 = 纬度
PHI_P = 180           # 面板朝向（南向）
A = 611111.11         # 面板面积（平方米）
ETA_REF = 0.18        # 标准效率
GAMMA = 0.0045        # 温度系数
KAPPA = 0.03          # 温升因子
RHO_G = 0.2           # 地面反射率
TAU_A = 0.15          # 气溶胶AOD
U_O = 0.3             # 臭氧厚度

# === 读取数据 === #
df = pd.read_excel('Solar station site 5 (Nominal capacity-110MW).xlsx')
df.columns = ['Time', 'Total', 'DNI', 'GHI', 'Temp', 'Pressure', 'RH', 'Power']
df['Time'] = pd.to_datetime(df['Time'])

# === 太阳天顶角计算函数（简化版） === #
def compute_zenith_angle(dt, lat):
    # 估算太阳高度角 H，简化模型（仅适用于中国区域）
    day_of_year = dt.timetuple().tm_yday
    hour_angle = 15 * ((dt.hour + dt.minute / 60) - 12)
    decl = 23.45 * np.sin(np.radians(360 * (284 + day_of_year) / 365))
    H = np.arcsin(np.sin(np.radians(lat)) * np.sin(np.radians(decl)) +
                  np.cos(np.radians(lat)) * np.cos(np.radians(decl)) * np.cos(np.radians(hour_angle)))
    zenith = np.degrees(np.pi/2 - H)
    return np.clip(zenith, 0, 90)

# === 入射角计算函数 === #
def compute_incidence_angle(zenith_deg, beta_deg, phi_sun_deg, phi_p_deg):
    z = radians(zenith_deg)
    b = radians(beta_deg)
    az_diff = radians(phi_sun_deg - phi_p_deg)
    cos_theta_i = cos(z) * cos(b) + sin(z) * sin(b) * cos(az_diff)
    return max(cos_theta_i, 0)

# === 大气透射率计算函数 === #
def compute_transmission_factors(row, zenith):
    m = 1 / (cos(np.radians(zenith)) + 0.50572 * (96.07995 - zenith)**-1.6364)

    Tr = np.exp(-0.0903 * (row['Pressure']/1013.25)**0.84 * (1 + cos(np.radians(zenith)))**-1.01)

    Ta = np.exp(-TAU_A * (0.6777 + 0.1464 * TAU_A - 0.00626 * TAU_A**2) * m)

    To = 1 - 0.011 * (U_O * m) / (1 + 0.006 * (U_O * m)**1.5)

    Uw = 0.1 * row['RH'] * np.exp(0.07 * row['Temp'])
    Tw = 1 - 0.077 * (Uw * m)**0.3

    Tg = np.exp(-0.0117 * m**0.3139)

    return Tr * Ta * To * Tw * Tg

# === 主计算循环 === #
P_theo = []

for i, row in df.iterrows():
    zenith = compute_zenith_angle(row['Time'], LAT)
    if zenith >= 90:
        P_theo.append(0)
        continue

    cos_theta_i = compute_incidence_angle(zenith, BETA, 180, PHI_P)
    DHI = row['GHI'] - row['DNI'] * cos(np.radians(zenith))
    G_eff = row['DNI'] * cos_theta_i + DHI * (1 + cos(np.radians(BETA))) / 2 + \
            RHO_G * row['GHI'] * (1 - cos(np.radians(BETA))) / 2

    eta = ETA_REF * (1 - GAMMA * (row['Temp'] + KAPPA * row['GHI'] - 25))
    T_total = compute_transmission_factors(row, zenith)

    p = eta * T_total * G_eff * A / 1e6  # 单位换算为MW
    P_theo.append(max(p, 0))

df['P_theo'] = P_theo

# === 可视化对比 === #
plt.figure(figsize=(12,5))
plt.plot(df['Time'], df['Power'], label='实际功率 (MW)', alpha=0.6)
plt.plot(df['Time'], df['P_theo'], label='理论功率 (MW)', alpha=0.8)
plt.legend(); plt.grid(); plt.title('理论 vs 实际光伏发电功率'); plt.xlabel('时间'); plt.ylabel('功率 (MW)')
plt.tight_layout(); plt.show()

# === 误差分析（简单） === #
df['Error'] = df['P_theo'] - df['Power']
print("均方根误差 RMSE：", np.sqrt(np.mean(df['Error']**2)))
print("平均误差 ME：", np.mean(df['Error']))
print("最大理论功率值：", np.max(df['P_theo']))
