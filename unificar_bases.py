import pandas as pd
import os
import re

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

dir_path = r"C:\Users\DiegoMeza\OneDrive - PARACEL S.A\MONITOREO_IMPACTO_SOCIAL_PARACEL\NAUTA PERCEPCIÓN INFORMES\encuesta_percepcion_2026"
file_bases = os.path.join(dir_path, "bases_2022al2026.xlsx")
output_file = os.path.join(dir_path, "BASE_CONSOLIDADA_SERIES.xlsx")

print("Leyendo archivo Excel...")
xl_bases = pd.ExcelFile(file_bases)

# Extraer 2024
df_2024 = xl_bases.parse("2024", header=1)
df_2024.rename(columns={
    'Número': 'id', 
    'Edades': 'edad',
    'Género': 'género',
    'Sector': 'sector',
    'Comunidad': 'comunidad',
    'NSE': 'nse'
}, inplace=True)
df_2024.columns = [clean_col_name(c) for c in df_2024.columns]
df_2024 = ensure_unique_columns(df_2024)
df_2024['año'] = 2024

# Extraer 2023
df_2023 = xl_bases.parse("2023", header=1)
df_2023.rename(columns={
    'Número': 'id',
    'Sector': 'sector',
    'Comunidad': 'comunidad',
    'NSE': 'nse'
}, inplace=True)
df_2023.columns = [clean_col_name(c) for c in df_2023.columns]
df_2023 = ensure_unique_columns(df_2023)
df_2023['año'] = 2023
df_2023['género'] = "No Registrado" 
df_2023['edad'] = "No Registrado" # 2023 no parece tener edad clara al principio

# Extraer 2022
df_2022 = xl_bases.parse("2022", header=1)
df_2022.rename(columns={
    'Num': 'id',
    'Edad': 'edad',
    'Componente': 'sector',
    'Comunidad:': 'comunidad',
    'Género:': 'género',
    'NSE': 'nse'
}, inplace=True)
df_2022.columns = [clean_col_name(c) for c in df_2022.columns]
df_2022 = ensure_unique_columns(df_2022)
df_2022['año'] = 2022

key_cols = ['año', 'id', 'género', 'edad', 'sector', 'comunidad', 'nse']

print("Concatenando datos...")
df_all = pd.concat([df_2024, df_2023, df_2022], ignore_index=True)

all_cols = list(df_all.columns)
first_cols = [c for c in key_cols if c in all_cols]
other_cols = [c for c in all_cols if c not in first_cols]
df_all = df_all[first_cols + other_cols]

print(f"Forma de la base unificada: {df_all.shape}")
print(f"Borrando columnas vacías...")
df_all.dropna(axis=1, how='all', inplace=True)
print(f"Forma de la base unificada después de limpieza: {df_all.shape}")

print(f"Guardando en {output_file} ...")
df_all.to_excel(output_file, index=False)
print("¡Archivo consolidado exitosamente!")
