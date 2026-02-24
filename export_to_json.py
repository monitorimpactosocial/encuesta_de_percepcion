import pandas as pd
import os
import json
import numpy as np

dir_path = r"C:\Users\DiegoMeza\OneDrive - PARACEL S.A\MONITOREO_IMPACTO_SOCIAL_PARACEL\NAUTA PERCEPCIÓN INFORMES\encuesta_percepcion_2026"
file_bases = os.path.join(dir_path, "BASE_CONSOLIDADA_SERIES_LIMPIA.xlsx")
output_js = os.path.join(dir_path, "data.js")

print("Cargando la base consolidada para web...")
df = pd.read_excel(file_bases)

# Limpiar NaN y casting especial
df.replace('-', np.nan, inplace=True)
year_col = [c for c in df.columns if 'año' in c.lower() or 'ano' in c.lower()]
if year_col:
    # Convert FLOAT years like 2025.0 -> '2025' reliably
    df[year_col[0]] = df[year_col[0]].apply(lambda x: str(int(x)) if pd.notnull(x) and str(x).strip() != '' and str(x).lower() != 'nan' else np.nan)

# Limpiar fechas NaT y NaN a cadenas vacías o string antes de to_dict
for col in df.columns:
    if pd.api.types.is_datetime64_any_dtype(df[col]):
        df[col] = df[col].astype(str).replace('NaT', None)

df = df.where(pd.notnull(df), None)

# --- INICIO LÓGICA DE DATOS PANEL E IMPUTACIÓN ---
print("Procesando cruce de datos Panel...")
import re

df['es_panel'] = "No" # Default value

# Buscar inteligentemente las columnas de nombre y celular sin importar variaciones de nombre
name_cols = [c for c in df.columns if 'nombre' in c.lower() and 'encuestado' in c.lower()]
phone_cols = [c for c in df.columns if 'telfono' in c.lower() or 'teléfono' in c.lower() or 'telefono' in c.lower()]
year_col = [c for c in df.columns if 'año' in c.lower() or 'ano' in c.lower()]

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

    # ID PANEL MEJORADO CON FUZZY MATCHING (difflib) Y REGLAS CRUZADAS
    import difflib
    
    # Vamos a crear una llave primaria estricta basada en teléfono, y para los que no tengan teléfono, agrupamos
    # por nombre similar dentro de la misma comunidad y género si es posible.
    # Dado que un O(N^2) puro en Python toma 1 segundo para 2000 registros, es totalmente viable.

    def generate_panel_ids(df_subset):
        # 1. Asignar IDs primero por telefono si es valido
        panel_dict = {}
        current_id = 0
        assigned_ids = [None] * len(df_subset)
        
        phones = df_subset['_clean_phone'].tolist()
        names = df_subset['_clean_name'].tolist()
        
        # Primero agrupar por telefonos idénticos validos
        for i, p in enumerate(phones):
            if len(p) > 4:
                # Buscar si este telefono ya se dio
                found_id = None
                for idx, existing_p in enumerate(phones[:i]):
                    if existing_p == p:
                        found_id = assigned_ids[idx]
                        break
                if found_id is not None:
                    assigned_ids[i] = found_id
                else:
                    assigned_ids[i] = f"PNL_{current_id}"
                    current_id += 1
                    
        # 2. Para los que no tienen telefono, agrupar por similitud de nombres (Fuzzy Matching > 85%)
        for i, n in enumerate(names):
            if assigned_ids[i] is None and len(n) > 5:
                found_id = None
                for idx, existing_n in enumerate(names[:i]):
                    if len(existing_n) > 5:
                        # Calcular similitud
                        sim = difflib.SequenceMatcher(None, n, existing_n).ratio()
                        if sim > 0.85:
                            found_id = assigned_ids[idx]
                            break
                if found_id is not None:
                    assigned_ids[i] = found_id
                else:
                    assigned_ids[i] = f"PNL_{current_id}"
                    current_id += 1
                    
        return assigned_ids

    df['id_panel'] = generate_panel_ids(df)

    # Agrupar y contar cuantas veces encuestamos al id_panel en diferentes años
    counts = df.dropna(subset=['id_panel']).groupby('id_panel')[y_col].nunique()
    panel_ids = counts[counts > 1].index.tolist()

    df['es_panel'] = df['id_panel'].apply(lambda x: "Sí" if x in panel_ids else "No")

    # Columnas demográficas a imputar longitudinalmente si están vacías (bfill / ffill)
    # Incluiremos edad extendida
    demog_cols = [c for c in df.columns if any(k in c.lower() for k in ['género', 'genero', 'edad', 'nse', 'comunidad', 'nivel de estudios', 'situación laboral', 'ocupacion', 'estado civil', 'hijos'])]

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

print(f"Total encuestados Panel identificados: {len(df[df['es_panel'] == 'Sí'])}")
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
