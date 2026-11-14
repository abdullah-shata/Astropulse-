import pandas as pd
import numpy as np
from datetime import datetime, timedelta

BASE_URL = "https://physionet.org/files/bidmc/1.0.0/bidmc_csv/"
astronaut_configs = [
    {"id": "ASTRO_01", "files": ["bidmc_01_Numerics.csv", "bidmc_05_Numerics.csv"], "env": "Artemis_DeepSpace", "grav": 0.0, "lat": 15, "day": 14, "crisis": "Hypoxia"},
    {"id": "ASTRO_02", "files": ["bidmc_02_Numerics.csv", "bidmc_06_Numerics.csv"], "env": "Mars_Transit", "grav": 0.0, "lat": 1200, "day": 85, "crisis": "Space_Radiation_Spike"},
    {"id": "ASTRO_03", "files": ["bidmc_03_Numerics.csv", "bidmc_07_Numerics.csv"], "env": "Lunar_Base", "grav": 0.16, "lat": 3, "day": 42, "crisis": "SANS_Fluid_Shift"},
    {"id": "ASTRO_04", "files": ["bidmc_04_Numerics.csv", "bidmc_08_Numerics.csv"], "env": "EVA_Spacewalk", "grav": 0.0, "lat": 2, "day": 60, "crisis": "Cardiovascular_EVA_Stress"},
]

all_astro_dfs = []
np.random.seed(42)
start_time = datetime(2026, 11, 13, 10, 0, 0)

print("جاري سحب البيانات الطبية الحقيقية من PhysioNet ودمجها مع معايير ناسا...")

for cfg in astronaut_configs:
    # 1. تحميل ودمج ملفين لكل رائد فضاء (~960 ثانية متصلة لكل رائد)
    dfs = []
    for fname in cfg["files"]:
        df_part = pd.read_csv(BASE_URL + fname)
        df_part.columns = df_part.columns.str.strip()
        dfs.append(df_part)
    
    df = pd.concat(dfs, ignore_index=True)
    n = len(df)
    
    # تنظيف القيم المفقودة في البيانات الحقيقية وتحويلها لـ float
    for col in ['HR', 'RESP', 'SpO2']:
        df[col] = pd.to_numeric(df[col], errors='coerce').interpolate(method='linear').bfill().ffill().astype(float)

    # 2. بناء التسلسل الزمني والبيئة الثابتة لكل رائد فضاء
    out = pd.DataFrame()
    out['timestamp'] = [start_time + timedelta(seconds=i) for i in range(n)]
    out['astronaut_id'] = cfg['id']
    out['mission_environment'] = cfg['env']
    out['gravity_level_g'] = cfg['grav']
    out['comm_latency_sec'] = cfg['lat']
    out['mission_day'] = cfg['day']
    
    # القراءات الحقيقية من PhysioNet
    out['heart_rate_bpm'] = df['HR'].astype(float)
    out['respiratory_rate_rpm'] = df['RESP'].astype(float)
    out['spo2_percent'] = df['SpO2'].astype(float).clip(94.0, 100.0)
    
    # مؤشرات فسيولوجية مرتبطة بالنبض الحقيقي (لضمان الترابط الفسيولوجي)
    hr_delta = out['heart_rate_bpm'] - out['heart_rate_bpm'].mean()
    out['systolic_bp_mmhg'] = (118.0 + 0.35 * hr_delta + np.random.normal(0, 1.5, n)).astype(float)
    out['diastolic_bp_mmhg'] = (76.0 + 0.20 * hr_delta + np.random.normal(0, 1.0, n)).astype(float)
    out['body_temp_c'] = (36.8 + np.cumsum(np.random.normal(0, 0.005, n))).clip(36.3, 37.3).astype(float)
    out['blood_sugar_mg_dl'] = (94.0 + np.cumsum(np.random.normal(0, 0.08, n))).clip(75.0, 115.0).astype(float)
    
    # مؤشرات ناسا الخاصة (CSA CANS, ARCHeR, SANS, Bone Loss)
    base_rad = 0.03 if cfg['env'] == 'ISS_LEO' else (0.11 if cfg['env'] == 'EVA_Spacewalk' else 0.075)
    out['neutron_radiation_msv_hr'] = (base_rad + np.random.normal(0, 0.003, n)).clip(0.01, 0.2).astype(float)
    out['sleep_hours_24h'] = round(np.random.uniform(6.5, 8.0), 1)
    out['mood_stress_score'] = 2
    out['intracranial_pressure_idx'] = (14.2 + np.cumsum(np.random.normal(0, 0.02, n))).clip(11.0, 17.5).astype(float)
    out['bone_density_loss_pct'] = round((cfg['day'] / 30.0) * (1.0 if cfg['grav'] == 0 else 0.4), 2)
    
    out['health_status'] = 'Normal'
    out['detected_nasa_risk'] = 'Healthy_Baseline'
    out['triage_protocol_action'] = 'Continue routine ARCHeR & Tempus Pro telemetry monitoring'
    
    # 3. حقن منحنى تدهور تدريجي (Gradual Degradation Curve) لمدة 90 ثانية (من الثانية 600 إلى 690)
    c_start, c_end = 600, 690
    c_len = c_end - c_start
    ramp = np.linspace(0, 1, c_len)
    
    if cfg['crisis'] == 'Hypoxia':
        out.loc[c_start:c_end-1, 'spo2_percent'] -= (9.5 * ramp)
        out.loc[c_start:c_end-1, 'heart_rate_bpm'] += (35.0 * ramp)
        out.loc[c_start:c_end-1, 'respiratory_rate_rpm'] += (11.0 * ramp)
        out.loc[c_start:c_start+39, 'health_status'] = 'Warning'
        out.loc[c_start+40:c_end-1, 'health_status'] = 'Critical'
        out.loc[c_start:c_end-1, 'detected_nasa_risk'] = 'Risk_of_Hypoxia'
        out.loc[c_start:c_end-1, 'triage_protocol_action'] = 'Administer 100% O2 via emergency mask; check cabin/EVA suit pressure'

    elif cfg['crisis'] == 'Space_Radiation_Spike':
        out.loc[c_start:c_end-1, 'neutron_radiation_msv_hr'] += (0.85 * ramp)
        out.loc[c_start:c_start+29, 'health_status'] = 'Warning'
        out.loc[c_start+30:c_end-1, 'health_status'] = 'Critical'
        out.loc[c_start:c_end-1, 'detected_nasa_risk'] = 'Space_Radiation_Exposure'
        out.loc[c_start:c_end-1, 'triage_protocol_action'] = 'Move crew to shielded storm shelter; administer radioprotective countermeasures'

    elif cfg['crisis'] == 'SANS_Fluid_Shift':
        out.loc[c_start:c_end-1, 'intracranial_pressure_idx'] += (9.0 * ramp)
        out.loc[c_start:c_end-1, 'systolic_bp_mmhg'] += (22.0 * ramp)
        out.loc[c_start:c_end-1, 'health_status'] = 'Warning'
        out.loc[c_start:c_end-1, 'detected_nasa_risk'] = 'SANS_Neuro_Ocular_Risk'
        out.loc[c_start:c_end-1, 'triage_protocol_action'] = 'Apply Thigh Cuffs (lower body fluid redistribution); perform Fundoscope scan'

    elif cfg['crisis'] == 'Cardiovascular_EVA_Stress':
        out.loc[c_start:c_end-1, 'heart_rate_bpm'] += (55.0 * ramp)
        out.loc[c_start:c_end-1, 'body_temp_c'] += (1.7 * ramp)
        out.loc[c_start:c_end-1, 'systolic_bp_mmhg'] -= (24.0 * ramp)
        out.loc[c_start:c_start+44, 'health_status'] = 'Warning'
        out.loc[c_start+45:c_end-1, 'health_status'] = 'Critical'
        out.loc[c_start:c_end-1, 'detected_nasa_risk'] = 'Cardiovascular_EVA_Stress'
        out.loc[c_start:c_end-1, 'triage_protocol_action'] = 'Halt EVA exertion; initiate oral rehydration & lower-body compression garment'

    all_astro_dfs.append(out)

final_df = pd.concat(all_astro_dfs, ignore_index=True)

# 4. تقريب الأرقام العشرية لتكون نظيفة وجاهزة للعرض والتدريب
cols_1_dec = [
    'heart_rate_bpm', 'respiratory_rate_rpm', 'spo2_percent',
    'systolic_bp_mmhg', 'diastolic_bp_mmhg', 'blood_sugar_mg_dl',
    'intracranial_pressure_idx'
]
for col in cols_1_dec:
    final_df[col] = final_df[col].round(1)

final_df['body_temp_c'] = final_df['body_temp_c'].round(2)
final_df['neutron_radiation_msv_hr'] = final_df['neutron_radiation_msv_hr'].round(4)

final_df.to_csv('astropulse_hybrid_real_dataset.csv', index=False)
print("تم بنجاح! إجمالي الصفوف الحقيقية المعايرة:", final_df.shape)
print(final_df['detected_nasa_risk'].value_counts())