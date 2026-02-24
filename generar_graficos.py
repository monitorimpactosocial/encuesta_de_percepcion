import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import os

# Configuración de estilo
sns.set_theme(style="whitegrid")
plt.rcParams['font.family'] = 'sans-serif'

dir_path = r"C:\Users\DiegoMeza\OneDrive - PARACEL S.A\MONITOREO_IMPACTO_SOCIAL_PARACEL\NAUTA PERCEPCIÓN INFORMES\encuesta_percepcion_2026"
file_bases = os.path.join(dir_path, "BASE_CONSOLIDADA_SERIES_LIMPIA.xlsx")
output_dir = os.path.join(dir_path, "graficos_series")

if not os.path.exists(output_dir):
    os.makedirs(output_dir)

print("Cargando datos limpios...")
df = pd.read_excel(file_bases)

# 1. Función auxiliar para calcular porcentajes de menciones por año
def plot_evolution(df, columns_to_plot, title, filename, ylabel="% de menciones"):
    # Agrupar por año y calcular el % de veces que cada columna tiene valor no nulo ni '-'
    years = sorted(df['año'].unique())
    
    data_plot = []
    
    for y in years:
        df_year = df[df['año'] == y]
        total_encuestas = len(df_year)
        
        row = {'Año': str(y)}
        for col in columns_to_plot:
            if col in df_year.columns:
                # Contar cuántos respondieron afirmativamente a esta opción
                # Asumimos que si no es nulo y no es '-', es una selección
                count = df_year[col].replace('-', np.nan).notna().sum()
                porcentaje = (count / total_encuestas) * 100
            else:
                porcentaje = 0
            row[col] = porcentaje
        data_plot.append(row)
        
    df_plot = pd.DataFrame(data_plot)
    
    # Graficar
    plt.figure(figsize=(10, 6))
    
    markers = ['o', 's', '^', 'D', 'v', '<', '>', 'p', '*', 'h']
    for i, col in enumerate(columns_to_plot):
        plt.plot(df_plot['Año'], df_plot[col], marker=markers[i % len(markers)], linewidth=2.5, label=col.title(), markersize=8)
        
        # Añadir etiquetas de datos
        for j, val in enumerate(df_plot[col]):
            if val > 0: # Solo poner etiqueta si es mayor a 0 para no saturar
                plt.text(j, val + 1.5, f"{val:.1f}%", ha='center', fontsize=9)

    plt.title(title, fontsize=14, pad=20, fontweight='bold')
    plt.ylabel(ylabel, fontsize=12)
    plt.xlabel('Año', fontsize=12)
    plt.ylim(0, max([df_plot[c].max() for c in columns_to_plot]) + 15)
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()
    
    filepath = os.path.join(output_dir, filename)
    plt.savefig(filepath, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Gráfico guardado: {filename}")

# 2. Definir grupos de variables a analizar

aspectos_positivos = [
    'tranquilidad', 
    'seguridad', 
    'la gente', 
    'oferta laboral', 
    'desarrollo del sector comercial y servicios'
]

aspectos_negativos = [
    'inseguridad', 
    'consumo de drogas', 
    'poca oferta laboral',
    'falta de caminos' # Si no existe, dará 0%
]

medios_comunicacion = [
    'radio',
    'tv',
    'redes sociales',
    'medios de prensa',
    'amigos conocidos'
]

percepcion_paracel = [
    'más puestos de trabajo para personas de la zona',
    'mejoras o nuevos caminos o rutas en zonas aledañas',
    'nuevos comercios alrededor de la planta',
    'formación laboral profesional de personas'
]


print("Generando gráficos...")
plot_evolution(df, aspectos_positivos, "Evolución de Aspectos Positivos de la Comunidad (2022-2024)", "evolucion_positivos.png")
plot_evolution(df, aspectos_negativos, "Evolución de Principales Problemas / Aspectos Negativos (2022-2024)", "evolucion_negativos.png")
plot_evolution(df, medios_comunicacion, "Evolución de Medios por los que se enteraron de Paracel", "evolucion_medios.png")
plot_evolution(df, percepcion_paracel, "Efectos Positivos Esperados de la Fábrica Paracel", "evolucion_expectativas_paracel.png")

print("\n¡Todos los gráficos han sido generados en la carpeta 'graficos_series'!")
