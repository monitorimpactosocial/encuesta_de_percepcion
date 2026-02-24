import pandas as pd
import os
import json
import numpy as np

dir_path = r"C:\Users\DiegoMeza\OneDrive - PARACEL S.A\MONITOREO_IMPACTO_SOCIAL_PARACEL\NAUTA PERCEPCIÓN INFORMES\encuesta_percepcion_2026"
file_bases = os.path.join(dir_path, "BASE_CONSOLIDADA_SERIES_LIMPIA.xlsx")
output_js = os.path.join(dir_path, "data.js")

print("Cargando la base consolidada para web...")
df = pd.read_excel(file_bases)

# Reemplazar '-' por nan y luego todos los nan por None (json null)
df.replace('-', np.nan, inplace=True)

# Limpiar fechas NaT y NaN a cadenas vacías o string antes de to_dict
for col in df.columns:
    if pd.api.types.is_datetime64_any_dtype(df[col]):
        df[col] = df[col].astype(str).replace('NaT', None)

df = df.where(pd.notnull(df), None)

# --- INICIO LÓGICA DE DATOS PANEL E IMPUTACIÓN ---
print("Procesando cruce de datos Panel...")
import re

# Buscar inteligentemente las columnas de nombre y celular sin importar variaciones de nombre
name_cols = [c for c in df.columns if 'nombre del encuestado' in c.lower()]
phone_cols = [c for c in df.columns if 'telfono' in c.lower() or 'teléfono' in c.lower()]
year_col = [c for c in df.columns if 'año' in c.lower()]

if name_cols and phone_cols and year_col:
    name_col = name_cols[0]
    phone_col = phone_cols[0]
    y_col = year_col[0]

    def clean_phone(p):
        if pd.isna(p) or p is None: return ""
        s = re.sub(r'\D', '', str(p))
        return s[-6:] # Match de los ultimos 6 digitos del movil

    def clean_name(n):
        if pd.isna(n) or n is None: return ""
        return str(n).strip().lower()

    df['_clean_phone'] = df[phone_col].apply(clean_phone)
    df['_clean_name'] = df[name_col].apply(clean_name)

    # El ID único es: PrimerNombre_Ultimos6Telefono. Requerimos al menos 5 digitos de celular
    df['id_panel'] = df.apply(lambda row: row['_clean_name'].split()[0] + "_" + row['_clean_phone'] if len(row['_clean_phone'])>4 else np.nan, axis=1)

    # Agrupar y contar cuantas veces encuestamos al id_panel en diferentes años
    counts = df.dropna(subset=['id_panel']).groupby('id_panel')[y_col].nunique()
    panel_ids = counts[counts > 1].index.tolist()

    df['es_panel'] = df['id_panel'].apply(lambda x: "Sí" if x in panel_ids else "No")

    # Columnas demográficas a imputar longitudinalmente si están vacías (bfill / ffill)
    demog_cols = [c for c in df.columns if any(k in c.lower() for k in ['género', 'edad', 'nse', 'comunidad', 'nivel de estudios'])]

    if demog_cols:
        # Reemplazar None temporales por np.nan para el backfill/forwardfill
        df[demog_cols] = df[demog_cols].replace({None: np.nan})
        
        # Agrupar por la persona (id_panel), ordenar por año, e imputar espacios vacíos tomando datos de sus otras olas
        df.sort_values(by=['id_panel', y_col], inplace=True)
        df[demog_cols] = df.groupby('id_panel')[demog_cols].transform(lambda x: x.ffill().bfill())
        
        # Devolver np.nan a str vacío o None
        df[demog_cols] = df[demog_cols].where(pd.notnull(df[demog_cols]), None)
    
    # Limpiar columnas auxiliares de calculo
    df.drop(columns=['_clean_phone', '_clean_name', 'id_panel'], inplace=True)

print(f"Total encuestados Panel identificados: {len(df[df.get('es_panel') == 'Sí'])}")
# --- FIN LÓGICA DE DATOS PANEL ---

# Eliminar columnas con info personal o innecesaria para proteger datos privadamente antes de exportar
cols_to_drop = [
    'nombre del encuestado',
    'nmero de telfono del encuestado',
    'número de teléfono del encuestado',
    'nmero de telfono',
    'número de teléfono',
    'coordenada x',
    'coordenada y'
]

df.drop(columns=[c for c in cols_to_drop if c in df.columns], errors='ignore', inplace=True)

# Convertir a minúsculas todos los strings para facilitar filtros y evitar problemas de case sensitive en JS
for col in df.columns:
    if df[col].dtype == object or df[col].dtype == str:
        df[col] = df[col].apply(lambda x: str(x).strip().title() if x is not None and isinstance(x, str) else x)

# Convertir todo a lista de diccionarios
records = df.to_dict(orient='records')

print(f"Generando {len(records)} registros...")
# Escribir el JS
with open(output_js, 'w', encoding='utf-8') as f:
    f.write("const encuestasData = ")
    json.dump(records, f, ensure_ascii=False, indent=2)
    f.write(";\n")

print(f"Data estática generada en {output_js}")
