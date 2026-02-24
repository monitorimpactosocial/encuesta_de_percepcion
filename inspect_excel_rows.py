import pandas as pd
import os

dir_path = r"C:\Users\DiegoMeza\OneDrive - PARACEL S.A\MONITOREO_IMPACTO_SOCIAL_PARACEL\NAUTA PERCEPCIÓN INFORMES\encuesta_percepcion_2026"
file_bases = os.path.join(dir_path, "bases_2022al2026.xlsx")

xl_bases = pd.ExcelFile(file_bases)

for anio in ["2024", "2023", "2022"]:
    df = xl_bases.parse(anio, header=None, nrows=5)
    print(f"\n--- PRIMERAS 5 FILAS DE {anio} ---")
    for i in range(5):
        row_vals = [str(x)[:30] for x in df.iloc[i].values[:15]]
        print(f"Row {i}: {row_vals}")
