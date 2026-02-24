import pandas as pd
import os

dir_path = r"C:\Users\DiegoMeza\OneDrive - PARACEL S.A\MONITOREO_IMPACTO_SOCIAL_PARACEL\NAUTA PERCEPCIÓN INFORMES\encuesta_percepcion_2026"
file_bases = os.path.join(dir_path, "BASE_CONSOLIDADA_SERIES.xlsx")
output_file = os.path.join(dir_path, "BASE_CONSOLIDADA_SERIES_LIMPIA.xlsx")

print("Cargando la base original consolidada...")
df = pd.read_excel(file_bases)

# 1. Unificar columnas de texto abierto que significan lo mismo
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
    'sexo': 'género'
}

# Aplicar las combinaciones consolidadas
for col_old, col_new in dict_rename.items():
    # Hay algunos acentos que pueden estar raros desde la terminal, usamos el nombre de columna tal cual están en df
    real_cols = df.columns.tolist()
    
    # Búsqueda difusa para no fallar por un tilde
    match_old = [c for c in real_cols if col_old.replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u').replace('ñ','n') == c.replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u').replace('ñ','n').replace('', '')]
    match_new = [c for c in real_cols if col_new.replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u').replace('ñ','n') == c.replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u').replace('ñ','n').replace('', '')]
    
    if len(match_old)>0:
        c_old = match_old[0]
        c_new = match_new[0] if len(match_new)>0 else col_new
        
        if c_new in df.columns:
            # Si ambas existen, combinarlas llenando nulos
            df[c_new] = df[c_new].fillna(df[c_old])
            df.drop(columns=[c_old], inplace=True)
        else:
            # Si la nueva no existe (ej. edaad -> edad, pero edad ya existe... esto no pasará porque edad lo forzamos a existir antes)
            df.rename(columns={c_old: c_new}, inplace=True)

# 2. Eliminar columnas que sean puramente "response", "response X" o "unnamed X"
cols_to_drop = [c for c in df.columns if 
                c.startswith('response') or 
                c.startswith('unnamed') or 
                c.startswith('otro especifique') or 
                c.startswith('open ended response')]

df.drop(columns=cols_to_drop, inplace=True, errors='ignore')

# 3. Eliminar espacios en blanco adicionales
df.columns = [str(c).strip() for c in df.columns]

print(f"Columnas resultantes tras limpieza: {len(df.columns)}")
df.to_excel(output_file, index=False)
print("¡Limpieza terminada exitosamente!")
