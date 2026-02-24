import pandas as pd
import numpy as np
import os
import re

dir_path = r"C:\Users\DiegoMeza\OneDrive - PARACEL S.A\MONITOREO_IMPACTO_SOCIAL_PARACEL\NAUTA PERCEPCIÓN INFORMES\encuesta_percepcion_2026"
file_bases = os.path.join(dir_path, "BASE_CONSOLIDADA_SERIES_LIMPIA.xlsx")

print("Cargando base de datos...")
df = pd.read_excel(file_bases)

# Identificar columnas de nombre y telefono
name_cols = [c for c in df.columns if 'nombre del encuestado' in c.lower()]
phone_cols = [c for c in df.columns if 'telfono' in c.lower() or 'teléfono' in c.lower()]
year_col = [c for c in df.columns if 'año' in c.lower()][0]

print(f"Columnas de Nombre encontradas: {name_cols}")
print(f"Columnas de Teléfono encontradas: {phone_cols}")

if name_cols and phone_cols:
    name_col = name_cols[0]
    phone_col = phone_cols[0]

    # Limpieza de textos para cruce
    def clean_phone(p):
        if pd.isna(p): return ""
        s = str(p)
        s = re.sub(r'\D', '', s) # solo numeros
        return s[-6:] # Ulmnos 6 digitos para mayor match considerando códigos de pais o prefijos

    def clean_name(n):
        if pd.isna(n): return ""
        s = str(n).strip().lower()
        return s

    df['_clean_phone'] = df[phone_col].apply(clean_phone)
    df['_clean_name'] = df[name_col].apply(clean_name)

    # Crear ID hash basado en nombre y telefono si telefono es largo suficiente
    df['id_panel'] = df.apply(lambda row: row['_clean_name'].split()[0] + "_" + row['_clean_phone'] if len(row['_clean_phone'])>4 else np.nan, axis=1)

    print("\nMuestra de IDs creados:")
    print(df[['id_panel', year_col, name_col, phone_col]].dropna().head(10))

    counts = df.groupby('id_panel')[year_col].nunique()
    panel_subjects = counts[counts > 1]
    
    print(f"\nSujetos únicos totales identificados temporalmente: {df['id_panel'].nunique()}")
    print(f"Sujetos que aparecen en MÁS de 1 ola (Panel potencial): {len(panel_subjects)}")
    
    if len(panel_subjects) > 0:
        print("\nDistribución de olas participadas por sujeto repetido:")
        print(counts[counts > 1].value_counts())
else:
    print("No se encontraron columnas de nombre o teléfono.")
