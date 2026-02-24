import pandas as pd
import os

dir_path = r"C:\Users\DiegoMeza\OneDrive - PARACEL S.A\MONITOREO_IMPACTO_SOCIAL_PARACEL\NAUTA PERCEPCIÓN INFORMES\encuesta_percepcion_2026"
file_bases = os.path.join(dir_path, "bases_2022al2026.xlsx")

xl_bases = pd.ExcelFile(file_bases)
df_2024 = xl_bases.parse("2024")
df_2023 = xl_bases.parse("2023")
df_2022 = xl_bases.parse("2022")

print("--- TOP 30 COLUMNAS DE CADA AÑO ---")
print(f"2024: {df_2024.columns.tolist()[:30]}\n")
print(f"2023: {df_2023.columns.tolist()[:30]}\n")
print(f"2022: {df_2022.columns.tolist()[:30]}\n")
