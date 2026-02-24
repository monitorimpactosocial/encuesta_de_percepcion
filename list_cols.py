import pandas as pd
import os

dir_path = r"C:\Users\DiegoMeza\OneDrive - PARACEL S.A\MONITOREO_IMPACTO_SOCIAL_PARACEL\NAUTA PERCEPCIÓN INFORMES\encuesta_percepcion_2026"
file_bases = os.path.join(dir_path, "BASE_CONSOLIDADA_SERIES_LIMPIA.xlsx")

df = pd.read_excel(file_bases)
cols = list(df.columns)
print(f"Total Cols Finales: {len(cols)}")
for i, c in enumerate(cols):
    print(f"{i}: {c}")
