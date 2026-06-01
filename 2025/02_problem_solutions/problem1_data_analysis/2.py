# -*- coding: utf-8 -*-
"""
Created on 2025/5/24 10:21

@author: Prince
"""
from pathlib import Path

import pandas as pd
import numpy as np
from math import sin, cos, tan, acos, atan2, radians, degrees, exp, pi
from datetime import datetime

SCRIPT_DIR = Path(__file__).resolve().parent

# ========== 1. 数据读取与预处理 ==========
file_path = SCRIPT_DIR / 'Solar station site 5 (Nominal capacity-110MW).xlsx'
df = pd.read_excel(file_path)
df.columns = ['Time', 'TSI', 'DNI', 'GHI', 'Air_Temp', 'Pressure', 'RH', 'Power']
df['Time'] = pd.to_datetime(df['Time'])
df['DayOfYear'] = df['Time'].dt.dayofyear
df['Hour'] = df['Time'].dt.hour + df['Time'].dt.minute / 60

# ========== 2. 地理与物理参数 ==========
latitude = 31.1708218  # 地点纬度
longitude = 115.0159244  # 地点经度
beta = latitude  # 面板倾角设为纬度
phi_p = 180  # 面板朝向，南
eta_ref = 0.18
gamma = 0.0045
kappa = 0.03
A = 611111.11  # 光伏板面积 m²
rho_g = 0.2  # 地面反射率
tau_a = 0.15  # AOD经验值
U_o = 0.3  # 臭氧柱厚
P0 = 1013.25  # 标准大气压 hPa

# ========== 3. 太阳角度计算函数 ==========
def solar_angles(day_of_year, hour, latitude):
    B = 2 * pi * (day_of_year - 81) / 364
    EoT = 9.87 * sin(2 * B) - 7.53 * cos(B) - 1.5 * sin(B)
    TC = 4 * (longitude - 120) + EoT  # 假设标准经度为120°
    LST = hour + TC / 60  # 本地太阳时

    decl = 23.45 * sin(2 * pi * (284 + day_of_year) / 365)
    omega = 15 * (LST - 12)

    theta_z = degrees(acos(
        sin(radians(latitude)) * sin(radians(decl)) +
        cos(radians(latitude)) * cos(radians(decl)) * cos(radians(omega))
    ))

    phi_s = degrees(atan2(
        -sin(radians(omega)),
        tan(radians(decl)) * cos(radians(latitude)) - sin(radians(latitude)) * cos(radians(omega))
    ))
    phi_s = (phi_s + 360) % 360
    return theta_z, phi_s

# ========== 4. 太阳角度批量计算 ==========
df['theta_z'], df['phi_s'] = zip(*df.apply(lambda row: solar_angles(row['DayOfYear'], row['Hour'], latitude), axis=1))

# ========== 5. 入射角与辐照度分解 ==========
df['cos_theta_i'] = np.cos(np.radians(df['theta_z'])) * np.cos(np.radians(beta)) + \
                    np.sin(np.radians(df['theta_z'])) * np.sin(np.radians(beta)) * \
                    np.cos(np.radians(df['phi_s'] - phi_p))
df['cos_theta_i'] = df['cos_theta_i'].clip(lower=0)

df['DHI'] = df['GHI'] - df['DNI'] * np.cos(np.radians(df['theta_z']))
df['DHI'] = df['DHI'].clip(lower=0)

df['Geff'] = df['DNI'] * df['cos_theta_i'] + \
             df['DHI'] * (1 + np.cos(np.radians(beta))) / 2 + \
             rho_g * df['GHI'] * (1 - np.cos(np.radians(beta))) / 2

# ========== 6. 大气透射率模型 ==========
df['ma'] = 1 / (np.cos(np.radians(df['theta_z'])) + 0.50572 * (96.07995 - df['theta_z']) ** -1.6364)

df['Tr'] = np.exp(-0.0903 * (df['Pressure'] / P0) ** 0.84 * (1 + np.cos(np.radians(df['theta_z']))) ** -1.01)
df['Ta'] = np.exp(-tau_a * (0.6777 + 0.1464 * tau_a - 0.00626 * tau_a ** 2) * df['ma'])
df['To'] = 1 - (0.011 * U_o * df['ma']) / (1 + 0.006 * (U_o * df['ma']) ** 1.5)

df['Uw'] = 0.1 * df['RH'] * np.exp(0.07 * df['Air_Temp'])
df['Tw'] = 1 - 0.077 * (df['Uw'] * df['ma']) ** 0.3

df['Tg'] = np.exp(-0.0117 * df['ma'] ** 0.3139)

df['Geff_star'] = df['Tr'] * df['Ta'] * df['To'] * df['Tw'] * df['Tg'] * df['Geff']

# ========== 7. 组件效率与理论功率 ==========
df['eta'] = eta_ref * (1 - gamma * (df['Air_Temp'] + kappa * df['GHI'] - 25))
df['P_theo'] = df['eta'] * df['Geff_star'] * A / 1e6  # 单位换算为MW

# ========== 8. 输出核心结果 ==========
result = df[['Time', 'Power', 'P_theo']].copy()
result.dropna(inplace=True)
print(result.head(10))  # 预览前10行结果
