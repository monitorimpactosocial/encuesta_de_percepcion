import pandas as pd
import numpy as np
import os
import re

dir_path = r"C:\Users\DiegoMeza\OneDrive - PARACEL S.A\MONITOREO_IMPACTO_SOCIAL_PARACEL\NAUTA PERCEPCIÓN INFORMES\encuesta_percepcion_2026"

file_2025 = os.path.join(dir_path, "tabulacion_2025", "Data", "Desktop", "2025_Tabulación_Paracel_Percepción.xlsx")
file_bases = os.path.join(dir_path, "BASE_CONSOLIDADA_SERIES_LIMPIA.xlsx")

print("Cargando nueva base 2025...")
# header=3 refers to the 4th row where specific options are listed
df_new = pd.read_excel(file_2025, header=3)
# Drop completely empty cols
df_new.dropna(axis=1, how='all', inplace=True)
# Drop total rows if any
df_new = df_new[df_new['Nro'].notna() & (df_new['Nro'] != 'Desc.')]

print(f"Registros válidos 2025: {len(df_new)}")

print("Cargando base histórica...")
df_hist = pd.read_excel(file_bases)

def clean_col(c):
    c = str(c).lower().strip()
    c = re.sub(r'[\r\n\t]', ' ', c)
    c = re.sub(r'[^\w\s]', '', c)
    c = re.sub(r'\s+', ' ', c).strip()
    # Específicos para evitar pérdida de acentos o arreglar caracteres
    c = c.replace('á', 'a').replace('é', 'e').replace('í', 'i').replace('ó', 'o').replace('ú', 'u')
    c = c.replace('', '') # Remove weird chars
    return c

# Limpiar headers de ambos dataframes de manera estandar
new_cols = {c: clean_col(c) for c in df_new.columns}
df_new.rename(columns=new_cols, inplace=True)

hist_cols = {c: clean_col(c) for c in df_hist.columns}
df_hist.rename(columns=hist_cols, inplace=True)

# Forzar año a 2025
df_new['ano'] = 2025

# Encontrar columnas comunes y no comunes
comunes = set(df_new.columns) & set(df_hist.columns)
print(f"Columnas que mapean directamente: {len(comunes)}")
print(f"Columnas solo en 2025: {set(df_new.columns) - set(df_hist.columns)}")

# Manejar columnas duplicadas
df_new = df_new.loc[:, ~df_new.columns.duplicated()]

# Limpiar strings en df_new para evitar saltos de linea
for c in df_new.select_dtypes(include=['object']).columns:
    df_new[c] = df_new[c].astype(str).str.strip().replace({'nan': np.nan, 'None': np.nan})

# Preparando append
print("Combinando bases de datos...")
df_consolidada = pd.concat([df_hist, df_new], ignore_index=True)

print(f"Total registros históricos: {len(df_hist)}")
print(f"Total registros nuevos finales: {len(df_consolidada)}")

df_consolidada.to_excel(file_bases, index=False)
print("Base Consolidada guardada exitosamente con los datos 2025 integrados!")
