import pandas as pd
import os
import difflib

dir_path = r"C:\Users\DiegoMeza\OneDrive - PARACEL S.A\MONITOREO_IMPACTO_SOCIAL_PARACEL\NAUTA PERCEPCIÓN INFORMES\encuesta_percepcion_2026"
file_bases = os.path.join(dir_path, "BASE_CONSOLIDADA_SERIES.xlsx")

print("Cargando la base de 137 columnas...")
df = pd.read_excel(file_bases)
cols = df.columns.tolist()

# Ignorar las columnas clave que ya sabemos que estn bien
key_cols = ['año', 'id', 'género', 'edad', 'sector', 'comunidad', 'nse']
other_cols = [c for c in cols if c not in key_cols]

print(f"Buscando coincidencias aproximadas en las {len(other_cols)} columnas restantes...\n")

# Vamos a agrupar aquellas con una similitud > 0.8
grouped_cols = []
processed = set()

for i, col1 in enumerate(other_cols):
    if col1 in processed: continue
    
    # Encontrar todas las similares a col1
    matches = difflib.get_close_matches(col1, other_cols, n=10, cutoff=0.75)
    
    if len(matches) > 1: # Si tiene pareja(s)
        print(f"Grupo encontrado:")
        for m in matches:
            print(f"  - {m}")
            processed.add(m)
        print("-" * 20)
    else:
        # Se queda sola
        processed.add(col1)

print("\n(Solo se muestran los grupos con similitud > 0.75)")
