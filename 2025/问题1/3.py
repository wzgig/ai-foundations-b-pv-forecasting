# -*- coding: utf-8 -*-
"""
Created on 2025/5/24 10:23

@author: Prince
"""
file_path = 'Solar station site 5 (Nominal capacity-110MW).xlsx'
import pandas as pd
import numpy as np
from math import sin, cos, tan, acos, atan2, radians, degrees, exp, pi
import matplotlib.pyplot as plt
import matplotlib.pyplot as plt

# 设置中文字体
plt.rcParams["font.family"] = ["SimHei", "WenQuanYi Micro Hei", "Heiti TC"]
plt.rcParams["axes.unicode_minus"] = False
# ========== 1. 数据读取与预处理 ==========
file_path = 'Solar station site 5 (Nominal capacity-110MW).xlsx'
df = pd.read_excel(file_path)
df.columns = ['Time', 'TSI', 'DNI', 'GHI', 'Air_Temp', 'Pressure', 'RH', 'Power']
df['Time'] = pd.to_datetime(df['Time'])
df['DayOfYear'] = df['Time'].dt.dayofyear
df['Hour'] = df['Time'].dt.hour + df['Time'].dt.minute / 60

# ========== 2. 地理与模型参数 ==========
latitude = 31.1708218
longitude = 115.0159244
beta = latitude
phi_p = 180
eta_ref = 0.18
gamma = 0.0045
kappa = 0.03
A = 611111.11
rho_g = 0.2
tau_a = 0.15
U_o = 0.3
P0 = 1013.25

# ========== 3. 太阳角度函数 ==========
def solar_angles(day_of_year, hour, latitude):
    B = 2 * pi * (day_of_year - 81) / 364
    EoT = 9.87 * sin(2 * B) - 7.53 * cos(B) - 1.5 * sin(B)
    TC = 4 * (longitude - 120) + EoT
    LST = hour + TC / 60
    decl = 23.45 * sin(2 * pi * (284 + day_of_year) / 365)
    omega = 15 * (LST - 12)
    theta_z = degrees(acos(
        sin(radians(latitude)) * sin(radians(decl)) +
        cos(radians(latitude)) * cos(radians(decl)) * cos(radians(omega))
    ))
    phi_s = degrees(atan2(
        -sin(radians(omega)),
        tan(radians(decl)) * cos(radians(latitude)) -
        sin(radians(latitude)) * cos(radians(omega))
    ))
    phi_s = (phi_s + 360) % 360
    return theta_z, phi_s

# ========== 4. 批量计算角度 ==========
df['theta_z'], df['phi_s'] = zip(*df.apply(lambda row: solar_angles(row['DayOfYear'], row['Hour'], latitude), axis=1))

# ========== 5. 理论功率建模 ==========
df['cos_theta_i'] = np.cos(np.radians(df['theta_z'])) * np.cos(np.radians(beta)) + \
                    np.sin(np.radians(df['theta_z'])) * np.sin(np.radians(beta)) * \
                    np.cos(np.radians(df['phi_s'] - phi_p))
df['cos_theta_i'] = df['cos_theta_i'].clip(lower=0)

df['DHI'] = (df['GHI'] - df['DNI'] * np.cos(np.radians(df['theta_z']))).clip(lower=0)

df['Geff'] = df['DNI'] * df['cos_theta_i'] + \
             df['DHI'] * (1 + np.cos(np.radians(beta))) / 2 + \
             rho_g * df['GHI'] * (1 - np.cos(np.radians(beta))) / 2

df['ma'] = 1 / (np.cos(np.radians(df['theta_z'])) + 0.50572 * (96.07995 - df['theta_z']) ** -1.6364)
df['Tr'] = np.exp(-0.0903 * (df['Pressure'] / P0) ** 0.84 * (1 + np.cos(np.radians(df['theta_z']))) ** -1.01)
df['Ta'] = np.exp(-tau_a * (0.6777 + 0.1464 * tau_a - 0.00626 * tau_a ** 2) * df['ma'])
df['To'] = 1 - (0.011 * U_o * df['ma']) / (1 + 0.006 * (U_o * df['ma']) ** 1.5)
df['Uw'] = 0.1 * df['RH'] * np.exp(0.07 * df['Air_Temp'])
df['Tw'] = 1 - 0.077 * (df['Uw'] * df['ma']) ** 0.3
df['Tg'] = np.exp(-0.0117 * df['ma'] ** 0.3139)

df['Geff_star'] = df['Tr'] * df['Ta'] * df['To'] * df['Tw'] * df['Tg'] * df['Geff']
df['eta'] = eta_ref * (1 - gamma * (df['Air_Temp'] + kappa * df['GHI'] - 25))
df['P_theo'] = df['eta'] * df['Geff_star'] * A / 1e6

# ========== 6. 长周期（季节性）分析 ==========
df['Month'] = df['Time'].dt.month
monthly_stats = df.groupby('Month')[['Power', 'P_theo']].mean()
monthly_stats['Efficiency'] = monthly_stats['Power'] / monthly_stats['P_theo']

# 月平均功率图
plt.figure(figsize=(12, 5))
plt.plot(monthly_stats.index, monthly_stats['Power'], label='实际功率', marker='o')
plt.plot(monthly_stats.index, monthly_stats['P_theo'], label='理论功率', marker='o')
plt.title('月平均功率')
plt.xlabel('月份')
plt.ylabel('功率（MW）')
plt.legend()
plt.grid(True)
plt.show()

# 效率变化图
plt.figure(figsize=(12, 4))
plt.plot(monthly_stats.index, monthly_stats['Efficiency'], label='利用效率', marker='o', color='green')
plt.title('月平均利用效率')
plt.xlabel('月份')
plt.ylabel('η = 实际/理论')
plt.grid(True)
plt.show()

# ========== 7. 短周期（日内）分析 ==========
# 可改日期：例如 2023-06-15
selected_date = pd.to_datetime('2023-06-15').date()
typical_day = df[df['Time'].dt.date == selected_date]

plt.figure(figsize=(14, 5))
plt.plot(typical_day['Time'], typical_day['Power'], label='实际功率')
plt.plot(typical_day['Time'], typical_day['P_theo'], label='理论功率')
plt.title(f'{selected_date} 日内功率变化')
plt.xlabel('时间')
plt.ylabel('功率（MW）')
plt.xticks(rotation=45)
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.show()

# ========== 8. 偏差统计分析 ==========
day_df = df[df['P_theo'] > 0.5].copy()
day_df['P_diff'] = day_df['P_theo'] - day_df['Power']
day_df['Rel_Error'] = day_df['P_diff'] / day_df['P_theo']

plt.figure(figsize=(10, 4))
plt.hist(day_df['Rel_Error'], bins=50, color='orange', edgecolor='k')
plt.title('白昼时段相对偏差分布')
plt.xlabel('相对误差 ε = (P_theo - P_actual)/P_theo')
plt.ylabel('频数')
plt.grid(True)
plt.show()

print("相对误差统计信息（白昼时段）:")
print(day_df['Rel_Error'].describe())
# ========== 9. 功率曲线对比 ==========
plt.figure(figsize=(12, 5))
plt.plot(df['Time'], df['Power'], label='实际功率', alpha=0.6)
plt.plot(df['Time'], df['P_theo'], label='理论功率', alpha=0.8)
plt.title('实际功率 vs 理论功率')
plt.xlabel('时间')
plt.ylabel('功率（MW）')
plt.legend()
plt.grid(True)
plt.show()
# ========== 10. 输出结果 ==========
result = df[['Time', 'Power', 'P_theo']].copy()
result.dropna(inplace=True)
print(result.head(10))  # 预览前10行结果