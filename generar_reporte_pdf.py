import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from fpdf import FPDF
import re
import os

# --- 1. CONFIGURACIÓN ---
dir_path = r"C:\Users\DiegoMeza\OneDrive - PARACEL S.A\MONITOREO_IMPACTO_SOCIAL_PARACEL\NAUTA PERCEPCIÓN INFORMES\encuesta_percepcion_2026"
file_path_limpia = os.path.join(dir_path, 'BASE_CONSOLIDADA_SERIES_LIMPIA.xlsx')

# --- 2. GENERACIÓN DE GRÁFICOS ESTRATÉGICOS ---
def crear_graficos(df):
    plt.style.use('seaborn-v0_8-muted')
    
    # 2.A Tendencia Longitudinal (Evolución de Positiva)
    resumen = df.groupby('año')['percepcion_final'].value_counts(normalize=True).unstack() * 100
    if 'Positiva' not in resumen.columns:
        resumen['Positiva'] = 0
        
    plt.figure(figsize=(10, 5))
    plt.plot(resumen.index, resumen['Positiva'], marker='o', color='#003366', linewidth=4, label='Percepción Positiva')
    plt.fill_between(resumen.index, resumen['Positiva'], color='#003366', alpha=0.1)
    
    # Asegurar que el eje X muestre años enteros
    plt.xticks(resumen.index, [str(int(x)) for x in resumen.index])
    
    plt.title('Trayectoria de Aceptación Social PARACEL (2022-2025)', fontsize=14)
    plt.ylabel('Porcentaje (%)', fontsize=12)
    plt.ylim(0, 100)
    plt.grid(True, alpha=0.3)
    
    for x, y in zip(resumen.index, resumen['Positiva']):
        plt.text(x, y + 2, f'{y:.1f}%', ha='center', va='bottom', fontweight='bold', color='#003366')
        
    plt.tight_layout()
    plt.savefig('grafico_kpi.png', dpi=300)
    plt.close()

    # 2.B Brecha Territorial 2025 (Positividad por Comunidad)
    df25 = df[df['año'] == 2025]
    if not df25.empty:
        dist = df25.groupby('comunidad')['percepcion_final'].value_counts(normalize=True).unstack()
        if 'Positiva' in dist.columns:
            dist_pos = dist['Positiva'].dropna().sort_values() * 100
            
            plt.figure(figsize=(10, 6))
            colors = ['#d9534f' if x < 50 else '#5cb85c' for x in dist_pos]
            ax = dist_pos.plot(kind='barh', color=colors)
            plt.title('Índice de Positividad por Comunidad (2025)', fontsize=14)
            plt.xlabel('Aprobación (%)', fontsize=12)
            
            for i, v in enumerate(dist_pos):
                ax.text(v + 1, i, f"{v:.1f}%", color='black', va='center')
                
            plt.tight_layout()
            plt.savefig('grafico_mapa.png', dpi=300)
            plt.close()
        else:
             print("Advertencia: No hay percepción positva en 2025 para el grafico comunitario.")
    else:
        print("Advertencia: No existen datos del año 2025 para graficar el mapa comunitario.")

# --- 3. CONSTRUCCIÓN DEL DOCUMENTO PDF ---
class ReporteDoctoral(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 16)
        self.set_text_color(0, 51, 102) # Paracel Blueish
        self.cell(0, 15, 'REPORTE EJECUTIVO: EVOLUCION DE IMPACTO SOCIAL', 0, 1, 'C')
        self.set_draw_color(0, 51, 102)
        self.line(10, 25, 200, 25)
        self.ln(10)

    def chapter_title(self, label):
        self.set_font('Arial', 'B', 13)
        self.set_text_color(0, 51, 102)
        self.set_fill_color(230, 240, 255)
        self.cell(0, 10, label, 0, 1, 'L', 1)
        self.ln(5)

    def chapter_body(self, text):
        self.set_font('Arial', '', 11)
        self.set_text_color(0, 0, 0)
        # FPDF1 doesn't handle full utf8 easily without a font import, so we encode/decode basically to ignore errors or we replace tricky chars
        text = text.replace('ó', 'o').replace('í','i').replace('á','a').replace('é','e').replace('ú','u').replace('ñ','n').replace('ó', 'o').replace('Ó','O')
        self.multi_cell(0, 6, text)
        self.ln(2)

def generar_pdf(df):
    pdf = ReporteDoctoral()
    pdf.add_page()
    
    # SECCIÓN 1: RESUMEN Y TENDENCIA
    pdf.chapter_title('1. Diagnostico de Percepcion Longitudinal')
    
    # Extraer el valor real de Positividad 2025 para que sea dinámico
    pct_25 = "0.0"
    df25 = df[df['año'] == 2025]
    if not df25.empty:
        vcounts = df25['percepcion_final'].value_counts(normalize=True) * 100
        if 'Positiva' in vcounts:
            pct_25 = f"{vcounts['Positiva']:.1f}"
            
    txt_resumen = (f"El analisis de la serie 2022-2025 revela una dinamica de 'campana de expectativas'. "
                   f"Tras un crecimiento sostenido impulsado por la visibilidad de obras e inversion, "
                   f"el año 2025 presenta un ajuste situandose en al {pct_25}% de aprobacion global.")
    pdf.chapter_body(txt_resumen)
    if os.path.exists('grafico_kpi.png'):
        pdf.image('grafico_kpi.png', x=15, w=180)
    pdf.ln(5)

    # SECCIÓN 2: HITOS Y CRISIS
    pdf.add_page()
    pdf.chapter_title('2. Correlacion de Hitos y Contexto Critico')
    hitos = ("- 2022: Entrada de Heinzel Holding y obtencion de Licencia de Cogeneracion.\n"
             "- 2023: Botadura de barcazas y consolidacion de la estructura industrial.\n"
             "- 2024: Pico historico de empleo directo (1.800 colaboradores) y 67k ha plantadas.\n"
             "- 2025: Contexto de desvinculacion y redefinicion de cronograma de creditos.")
    pdf.chapter_body(hitos)

    # SECCIÓN 3: RECOMENDACIONES PERSONALIZADAS
    pdf.chapter_title('3. Estrategia y Desglose Comunitario')
    if os.path.exists('grafico_mapa.png'):
        pdf.image('grafico_mapa.png', x=15, w=180)
    pdf.ln(5)
    recom = ("Se recomienda activar la comunicacion de la estrategia de 'Ganancia Neta Ambiental' detallada "
             "en el Reporte de Sostenibilidad. Es imperativo transparentar el cumplimiento ambiental, la gestion "
             "de polvo/vialidad y las medidas de prevencion de contaminacion ante las comunidades más reticentes "
             "(barras rojas) para sostener la licencia social para operar.")
    pdf.chapter_body(recom)

    output_name = 'Reporte_Gerencial_Social_2026.pdf'
    pdf.output(output_name)
    print(f"Reporte PDF generado exitosamente: {output_name}")

if __name__ == "__main__":
    print("Cargando datos maestros limpios...")
    df_f = pd.read_excel(file_path_limpia)
    
    print("Generando graficos en disco...")
    crear_graficos(df_f)
    
    print("Ensamblando documento FPDF...")
    generar_pdf(df_f)
    
    # Limpiar PNGs temporales
    if os.path.exists('grafico_kpi.png'): os.remove('grafico_kpi.png')
    if os.path.exists('grafico_mapa.png'): os.remove('grafico_mapa.png')
    
    print("¡Proceso Terminado!")
