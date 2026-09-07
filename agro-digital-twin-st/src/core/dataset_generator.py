"""
Módulo Generador y Gestor del Dataset Eco-Hidrológico para AgroTwin-AI.
Implementa el motor de síntesis y calibración física basado en SWAT, FAO-56 y Feddes.
"""

import os
import math
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from src.utils.config import DATASET_RAW_PATH, DATASET_CLEANED_PATH

def generate_ecohydrological_dataset(num_days: int = 1825, seed: int = 42) -> pd.DataFrame:
    """
    Genera un dataset multivariable calibrado biofísicamente para 5 años de monitoreo.
    Incluye dinámicas estacionales, olas de calor, recarga por precipitación y
    curvas de absorción radicular de Feddes para palto Hass.
    """
    np.random.seed(seed)
    records = []
    
    start_date = datetime(2021, 1, 1)
    
    # Parámetros edáficos y de cultivo
    theta_sat = 44.0   # Saturación (%)
    theta_fc = 32.0    # Capacidad de campo (%)
    theta_wp = 12.0    # Punto de marchitez permanente (%)
    theta_crit = theta_wp + 0.55 * (theta_fc - theta_wp) # 23.0%
    
    current_soil_moist = 26.5
    antecedent_precip_buffer = [0.0, 0.0, 0.0]
    
    for i in range(num_days):
        curr_date = start_date + timedelta(days=i)
        doy = curr_date.timetuple().tm_yday # Day of Year (1 - 365)
        
        # Estacionalidad climática (Hemisferio Sur / Valle semiárido)
        # Verano (Ene-Mar): cálido y algo lluvioso. Invierno (Jun-Ago): fresco y seco.
        season_phase = math.sin(2 * math.pi * (doy - 80) / 365.25)
        
        # Temperatura (°C)
        t_base = 22.0 + 7.5 * season_phase
        temp_noise = np.random.normal(0, 1.8)
        
        # Olas de calor súbitas estocásticas (5% de probabilidad en verano)
        heatwave_shock = 5.0 if (season_phase > 0.5 and np.random.rand() < 0.08) else 0.0
        
        temp_max = round(t_base + 5.5 + temp_noise + heatwave_shock, 2)
        temp_min = round(t_base - 5.5 + temp_noise * 0.7, 2)
        temp_mean = round((temp_max + temp_min) / 2.0, 2)
        
        # Radiación solar (MJ/m2/d)
        solar_rad = round(max(10.0, 21.0 + 6.0 * season_phase + np.random.normal(0, 2.2)), 2)
        
        # Humedad relativa (%)
        rh_mean = round(max(25.0, min(88.0, 60.0 - 15.0 * season_phase - (temp_max - 25.0) * 1.2 + np.random.normal(0, 4.0))), 2)
        
        # Déficit de Presión de Vapor - VPD (kPa)
        # VPD = es(T) - ea = 0.6108 * exp(17.27*T/(T+237.3)) * (1 - RH/100)
        es = 0.6108 * math.exp(17.27 * temp_mean / (temp_mean + 237.3))
        ea = es * (rh_mean / 100.0)
        vpd_kpa = round(max(0.2, es - ea), 3)
        
        # Viento (m/s)
        wind_speed = round(max(0.5, 2.2 + 0.8 * season_phase + np.random.normal(0, 0.6)), 2)
        
        # Precipitación (mm/día) — Ocurrencia estocástica tipo Poisson / Gamma
        is_rainy_season = (doy < 100 or doy > 320)
        rain_prob = 0.22 if is_rainy_season else 0.04
        if np.random.rand() < rain_prob:
            precip_mm = round(float(np.random.gamma(shape=2.0, scale=6.5)), 2)
        else:
            precip_mm = 0.0
            
        antecedent_precip_buffer.append(precip_mm)
        if len(antecedent_precip_buffer) > 3:
            antecedent_precip_buffer.pop(0)
        precip_3d = round(sum(antecedent_precip_buffer), 2)
        
        # Evapotranspiración de Referencia ET0 (FAO-56 Turc / Penman)
        et0 = 0.013 * (temp_mean / (temp_mean + 15.0)) * (23.885 * (solar_rad * 0.408) + 50.0)
        if rh_mean < 50.0:
            et0 *= (1.0 + (50.0 - rh_mean) / 70.0)
        et0_mm = round(max(0.8, et0), 2)
        
        # Caudal fluvial de cuenca SWAT (m3/s)
        baseflow = 5.0 + 3.0 * season_phase
        quickflow = precip_mm * 0.45 + precip_3d * 0.15
        streamflow_m3s = round(max(2.0, baseflow + quickflow + np.random.normal(0, 0.4)), 2)
        
        # Dinámica del suelo (Infiltración - Percolación - Transpiración)
        # Recarga por lluvia
        soil_recharge = precip_mm * 0.65
        current_soil_moist += soil_recharge
        if current_soil_moist > theta_sat:
            percolation = current_soil_moist - theta_sat
            current_soil_moist = theta_sat
        else:
            percolation = max(0.0, (current_soil_moist - theta_fc) * 0.25)
            current_soil_moist -= percolation
            
        # Reducción de Feddes para transpiración vegetal
        theta = max(theta_wp - 2.0, min(theta_sat, current_soil_moist))
        if theta >= theta_crit:
            alpha_feddes = 1.0
        elif theta > theta_wp:
            alpha_feddes = (theta - theta_wp) / (theta_crit - theta_wp)
        else:
            alpha_feddes = 0.05
            
        potential_transpiration = et0_mm * 1.05
        actual_transpiration = round(potential_transpiration * alpha_feddes, 2)
        
        # Extracción radicular del suelo
        current_soil_moist = max(theta_wp - 2.0, current_soil_moist - (actual_transpiration / 8.0))
        
        # Ruido de sensor TDR/Capacitivo (+- 0.5% vol)
        sensor_moist_vol = round(current_soil_moist + np.random.normal(0, 0.4), 2)
        
        # Target 1: CWSI (Crop Water Stress Index) continuo [0, 1]
        cwsi = round(1.0 - (actual_transpiration / max(0.1, potential_transpiration)), 3)
        cwsi = max(0.0, min(1.0, cwsi))
        
        # Target 2: Categoría de estrés (0: Óptimo, 1: Moderado, 2: Crítico)
        if cwsi < 0.25:
            stress_category = 0
        elif cwsi < 0.55:
            stress_category = 1
        else:
            stress_category = 2
            
        # Target 3: Demanda de Riego Inteligente (Lámina neta en mm)
        # Si está en estrés, se calcula la lámina para llevar el suelo a Capacidad de Campo
        if current_soil_moist < theta_crit:
            deficit_vol = theta_fc - current_soil_moist
            # Riego neto = Deficit (% vol / 100) * Profundidad radicular (1200 mm)
            irrigation_need = round(max(0.0, (deficit_vol / 100.0) * 800.0 * 0.15 + (cwsi * 3.5)), 2)
        else:
            irrigation_need = 0.0
            
        records.append({
            "day_index": i + 1,
            "date": curr_date.strftime("%Y-%m-%d"),
            "temp_max": temp_max,
            "temp_min": temp_min,
            "temp_mean": temp_mean,
            "solar_rad": solar_rad,
            "rh_mean": rh_mean,
            "vpd_kpa": vpd_kpa,
            "wind_speed": wind_speed,
            "precip_mm": precip_mm,
            "precip_3d": precip_3d,
            "streamflow_m3s": streamflow_m3s,
            "soil_moisture_vol": sensor_moist_vol,
            "et0_mm": et0_mm,
            "actual_transpiration_mm": actual_transpiration,
            "cwsi_stress_index": cwsi,
            "stress_category": stress_category,
            "irrigation_need_mm": irrigation_need
        })
        
    df = pd.DataFrame(records)
    return df


def get_dataset(force_regenerate: bool = False) -> pd.DataFrame:
    """
    Carga el dataset existente o lo genera automáticamente si no está en disco.
    """
    os.makedirs(os.path.dirname(DATASET_RAW_PATH), exist_ok=True)
    
    if os.path.exists(DATASET_RAW_PATH) and not force_regenerate:
        df = pd.read_csv(DATASET_RAW_PATH)
    else:
        df = generate_ecohydrological_dataset()
        df.to_csv(DATASET_RAW_PATH, index=False)
        # Guardar copia limpia
        df.to_csv(DATASET_CLEANED_PATH, index=False)
        print(f"✅ Dataset eco-hidrológico generado exitosamente con {len(df)} registros en {DATASET_RAW_PATH}")
        
    return df
