import pandas as pd
import numpy as np
import os
import re

dir_path = r"C:\Users\DiegoMeza\OneDrive - PARACEL S.A\MONITOREO_IMPACTO_SOCIAL_PARACEL\NAUTA PERCEPCIÓN INFORMES\encuesta_percepcion_2026"

files = {
    '2022': os.path.join(dir_path, 'bases_originales', '2022_Tabulación_Paracel Línea de Base Percepción.xlsx'),
    '2023': os.path.join(dir_path, 'bases_originales', '2023_Tabulación_Línea de Salida.xlsx'),
    '2024': os.path.join(dir_path, 'bases_originales', '2024_Tabulación Quanti_Paracel.xlsx'),
    '2025': os.path.join(dir_path, 'tabulacion_2025', 'Data', 'Desktop', '2025_Tabulación_Paracel_Percepción.xlsx')
}

output_file = os.path.join(dir_path, "BASE_CONSOLIDADA_SERIES_LIMPIA.xlsx")

def imputar_genero(nombre, genero_actual):
    if pd.notna(genero_actual) and str(genero_actual).strip().lower() in ['hombre', 'mujer', 'masculino', 'femenino']:
        return str(genero_actual).strip().capitalize()
    
    if pd.isna(nombre) or not str(nombre).strip():
        return np.nan
        
    nombre = str(nombre).strip().upper()
    primer_nombre = nombre.split()[0]
    
    males = ['JOSE', 'JUAN', 'LUIS', 'CARLOS', 'JORGE', 'MANUEL', 'PEDRO', 'MIGUEL', 'DIEGO', 'ANGEL', 'JESUS', 'FRANCISCO', 'ANTONIO', 'DAVID', 'FERNANDO', 'RUBEN', 'OSCAR', 'DANIEL', 'ALEJANDRO', 'ROBERTO', 'ARIEL', 'HUGO', 'NELSON', 'RAFAEL', 'CRISTIAN', 'RICHARD', 'MARTIN', 'ALCIDES', 'OSVALDO', 'GUSTAVO', 'ALFREDO', 'LUCAS', 'JULIO', 'MARIO', 'EDGAR', 'DERLIS']
    females = ['MARIA', 'CARMEN', 'ANA', 'LOURDES', 'BLANCA', 'NILDA', 'ZULMA', 'GLADYS', 'NANCY', 'TERESA', 'ROSA', 'MIRIAN', 'RAMONA', 'SILVIA', 'ELIZABETH', 'NORMA', 'EVELYN', 'MONICA', 'RUT', 'LUZ', 'LILIANA', 'GLORIA', 'SONIA', 'MARTA', 'ANDREA', 'BEATRIZ', 'ROBERTA', 'JUANA']
    
    if primer_nombre in males: return 'Hombre'
    if primer_nombre in females: return 'Mujer'
    
    if primer_nombre.endswith('A'):
        return 'Mujer'
    elif primer_nombre.endswith('O') or primer_nombre.endswith('E') or primer_nombre.endswith('S') or primer_nombre.endswith('N') or primer_nombre.endswith('R'):
        return 'Hombre'
    
    return np.nan

def clean_col_name(name):
    if pd.isna(name):
        return ""
    name = str(name).strip().lower()
    name = name.replace(":", "")
    name = re.sub(r"[^a-záéíóúñ0-9 ]+", " ", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name

def ensure_unique_columns(df):
    cols = []
    seen = {}
    for c in df.columns:
        if c in seen:
            seen[c] += 1
            cols.append(f"{c}_{seen[c]}")
        else:
            seen[c] = 0
            cols.append(c)
    df.columns = cols
    return df

dict_rename = {
    'seguridad 1': 'seguridad',
    'menores de 18 años': 'menor a 18 años',
    'cuál es tu relación actual con paracel 1': 'cuál es tu relación actual con paracel',
    'algún comentario más que quieras dejar a paracel cerrado': 'algún comentario más que quieras dejar a paracel',
    'qué crees que producirá la fábrica de paracel 1': 'qué crees que producirá la fábrica de paracel',
    'qué crees que producirá la fábrica de paracel 2': 'qué crees que producirá la fábrica de paracel',
    'conoces alguna actividad que paracel está realizando en las comunidades cercanas a la zona de la fábrica 1': 'conoces alguna actividad que paracel está realizando en las comunidades cercanas a la zona de la fábrica',
    'conoces alguna actividad que paracel está realizando en las comunidades cercanas a la zona de la fábrica 2': 'conoces alguna actividad que paracel está realizando en las comunidades cercanas a la zona de la fábrica',
    'sí cuáles_1': 'sí cuáles',
    'sí cuáles 1': 'sí cuáles',
    'sí cuáles 1_1': 'sí cuáles',
    'edaad': 'edad',
    'sexo': 'género',
    'nombre del encuestado': 'nombre'
}

list_dfs = []

# --- 2024 ---
print("Procesando 2024...")
df_2024 = pd.read_excel(files['2024'], sheet_name=0, header=1)
df_2024.rename(columns={'Número': 'id', 'Edades': 'edad', 'Género:': 'género', 'Sector': 'sector', 'Comunidad': 'comunidad', 'NSE': 'nse'}, inplace=True)
df_2024.columns = [clean_col_name(c) for c in df_2024.columns]
df_2024 = ensure_unique_columns(df_2024)
df_2024['año'] = 2024
list_dfs.append(df_2024)

# --- 2023 ---
print("Procesando 2023...")
df_2023 = pd.read_excel(files['2023'], sheet_name=0, header=1)
df_2023.rename(columns={'Número': 'id', 'Sector': 'sector', 'Comunidad': 'comunidad', 'NSE': 'nse', 'la gente': 'género'}, inplace=True)
df_2023.columns = [clean_col_name(c) for c in df_2023.columns]
df_2023 = ensure_unique_columns(df_2023)
df_2023['año'] = 2023
list_dfs.append(df_2023)

# --- 2022 ---
print("Procesando 2022...")
df_2022 = pd.read_excel(files['2022'], sheet_name=0, header=1)
df_2022.rename(columns={'Num': 'id', 'Edad': 'edad', 'Componente': 'sector', 'Comunidad:': 'comunidad', 'Género:': 'género', 'NSE': 'nse'}, inplace=True)
df_2022.columns = [clean_col_name(c) for c in df_2022.columns]
df_2022 = ensure_unique_columns(df_2022)
df_2022['año'] = 2022
list_dfs.append(df_2022)

# Unir inicial 2022-2024
print("Concatenando 2022-2024...")
df_hist = pd.concat(list_dfs, ignore_index=True)

# Imputar Género en df_hist (2022-2024)
print("Imputando Género 2022-2024 a partir del Nombre...")
col_nombre = next((c for c in df_hist.columns if 'nombre' in c), None)
col_sexo = next((c for c in df_hist.columns if 'gén' in c or 'sexo' in c), None)

if col_nombre and col_sexo:
    df_hist[col_sexo] = df_hist.apply(lambda row: imputar_genero(row[col_nombre], row[col_sexo]), axis=1)
else:
    print(f"ADVERTENCIA: No se encontró col_nombre o col_sexo. Nombre: {col_nombre}, Sexo: {col_sexo}")

# --- 2025 ---
print("Procesando 2025...")
df_2025 = pd.read_excel(files['2025'], header=3)
df_2025.dropna(axis=1, how='all', inplace=True)
df_2025 = df_2025[df_2025['Nro'].notna() & (df_2025['Nro'] != 'Desc.')]
df_2025.columns = [clean_col_name(c) for c in df_2025.columns]
df_2025 = ensure_unique_columns(df_2025)
df_2025['año'] = 2025

# Unir histórico con 2025
print("Consolidando con 2025...")
df_all = pd.concat([df_hist, df_2025], ignore_index=True)

# Renombrar columnas comunes usando dict
print("Renombrando columnas por diccionario...")
for col_old, col_new in dict_rename.items():
    real_cols = df_all.columns.tolist()
    match_old = [c for c in real_cols if col_old.replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u') == c.replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u')]
    match_new = [c for c in real_cols if col_new.replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u') == c.replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u')]
    
    if len(match_old) > 0:
        c_old = match_old[0]
        c_new = match_new[0] if len(match_new) > 0 else col_new
        if c_new in df_all.columns:
            df_all[c_new] = df_all[c_new].fillna(df_all[c_old])
            df_all.drop(columns=[c_old], inplace=True)
        else:
            df_all.rename(columns={c_old: c_new}, inplace=True)

# Normalizar Generos
print("Estandarizando género final...")
def normalizar_genero(v):
    if pd.isna(v): return "No Registrado"
    v = str(v).lower()
    if 'mujer' in v or 'femenino' in v: return 'Mujer'
    if 'hombre' in v or 'masculino' in v: return 'Hombre'
    return 'No Registrado'

val_genero = 'género' if 'género' in df_all.columns else 'sexo'
if val_genero in df_all.columns:
    df_all[val_genero] = df_all[val_genero].apply(normalizar_genero)

# Normalizar Edades
print("Estandarizando edades en rangos...")
def normalizar_edad(v):
    if pd.isna(v): return "No registrado"
    v_str = str(v).lower().strip()
    
    # Matching existing ranges
    if '18 a 19' in v_str: return '18 a 19 años'
    if '20 a 29' in v_str: return '20 a 29 años'
    if '30 a 39' in v_str: return '30 a 39 años'
    if '40 a 49' in v_str: return '40 a 49 años'
    if '50 a 59' in v_str: return '50 a 59 años'
    if '60 ' in v_str and (' o ' in v_str or ' a ' in v_str or ' m' in v_str): return '60 años o más'
    if '50 ' in v_str and (' o ' in v_str or ' m' in v_str): return '50 años o más'
    
    # Matching strict numerics
    try:
        age = int(float(v))
        if 18 <= age <= 19: return '18 a 19 años'
        elif 20 <= age <= 29: return '20 a 29 años'
        elif 30 <= age <= 39: return '30 a 39 años'
        elif 40 <= age <= 49: return '40 a 49 años'
        elif 50 <= age <= 59: return '50 a 59 años'
        elif age >= 60: return '60 años o más'
        else: return 'Menor a 18 años'
    except:
        return "No registrado"

if 'edad' in df_all.columns:
    df_all['edad'] = df_all['edad'].apply(normalizar_edad)

# Limpiar restos
cols_to_drop = [c for c in df_all.columns if c.startswith('response') or c.startswith('unnamed') or c.startswith('otro especifique') or c.startswith('open ended response')]
df_all.drop(columns=cols_to_drop, inplace=True, errors='ignore')

df_all.dropna(axis=1, how='all', inplace=True)

print(f"Guardando {output_file}...")
df_all.to_excel(output_file, index=False)
print("¡Archivo consolidado, imputado y limpio generado exitosamente!")
