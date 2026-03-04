import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from fpdf import FPDF
import re
import os

# --- 1. CONFIGURACIÓN ---
dir_path = r"C:\Users\DiegoMeza\OneDrive - PARACEL S.A\MONITOREO_IMPACTO_SOCIAL_PARACEL\NAUTA PERCEPCIÓN INFORMES\encuesta_percepcion_2026"
file_path_limpia = os.path.join(dir_path, 'BASE_CONSOLIDADA_SERIES_LIMPIA.xlsx')
logo_path = os.path.join(os.path.dirname(dir_path), 'LOGO_PARACEL_SINFONDO.png')
output_name = 'Reporte_Integral_Impacto_Social_2026.pdf'

# --- 2. GENERACIÓN DE GRÁFICOS MATPLOTLIB ---
def crear_graficos(df):
    plt.style.use('seaborn-v0_8-whitegrid')
    
    # helper de limpieza
    def trunc(s): return str(s)[:25] + ('...' if len(str(s))>25 else '')
    
    # 2.A: Tendencia (Evolución de Positividad)
    resumen = df.groupby('año')['percepcion_final'].value_counts(normalize=True).unstack() * 100
    if 'Positiva' not in resumen.columns: resumen['Positiva'] = 0
    plt.figure(figsize=(10, 4.5))
    plt.plot(resumen.index, resumen['Positiva'], marker='o', color='#004b2b', linewidth=3, markersize=8) # Paracel Green
    plt.fill_between(resumen.index, resumen['Positiva'], color='#004b2b', alpha=0.1)
    plt.xticks(resumen.index, [str(int(x)) for x in resumen.index], fontsize=11)
    plt.title('Evolución Histórica de Aceptación Social (2022-2025)', fontsize=13, fontweight='bold', color='#333333')
    plt.ylabel('Aprobación Global (%)', fontsize=11)
    plt.ylim(0, max(resumen['Positiva'])+15)
    for x, y in zip(resumen.index, resumen['Positiva']): plt.text(x, y + 2.5, f'{y:.1f}%', ha='center', va='bottom', fontweight='bold', color='#004b2b', fontsize=11)
    plt.tight_layout(); plt.savefig('grafico_kpi_tendencia.png', dpi=300); plt.close()

    # 2.B: Mapa de Calor por Comunidades (2025)
    df25 = df[df['año'] == 2025]
    if not df25.empty:
        dist = df25.groupby('comunidad')['percepcion_final'].value_counts(normalize=True).unstack().fillna(0)
        if 'Positiva' in dist.columns:
            dist_pos = dist['Positiva'].sort_values() * 100
            plt.figure(figsize=(10, 6))
            colors = ['#c0392b' if x < 50 else '#27ae60' for x in dist_pos]
            ax = dist_pos.plot(kind='barh', color=colors)
            plt.title('Radio de Positividad Social por Distrito / Comunidad (2025)', fontsize=13, fontweight='bold', color='#333333')
            plt.xlabel('Tasa de Aprobación (%)', fontsize=11)
            for i, v in enumerate(dist_pos): ax.text(v + 1.5, i, f"{v:.1f}%", color='black', va='center', fontsize=9, fontweight='bold')
            plt.tight_layout(); plt.savefig('grafico_mapa_comunas.png', dpi=300); plt.close()

    # 2.C: Demografía (Género y NSE)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 5))
    # Genero
    gen_dist = df['género'].value_counts(normalize=True) * 100
    ax1.pie(gen_dist, labels=[trunc(l) for l in gen_dist.index], autopct='%1.1f%%', startangle=140, colors=['#3498db', '#e74c3c', '#95a5a6'])
    ax1.set_title('Distribución Histórica de Género', fontweight='bold')
    # NSE
    nse_dist = df['nse'].value_counts(normalize=True) * 100
    ax2.pie(nse_dist, labels=[trunc(l) for l in nse_dist.index], autopct='%1.1f%%', startangle=90, colors=['#f1c40f', '#e67e22', '#16a085', '#bdc3c7'])
    ax2.set_title('Conformación del Nivel Socioeconómico', fontweight='bold')
    plt.tight_layout(); plt.savefig('grafico_demografia.png', dpi=300); plt.close()
    
    # 2.D: Estudios (Barras Horizontales)
    est_dist = df['estudios'].value_counts(normalize=True).sort_values() * 100
    plt.figure(figsize=(9, 4))
    est_dist.plot(kind='barh', color='#8e44ad')
    plt.title('Instrucción Académica Predominante del Panel', fontweight='bold')
    plt.xlabel('Porcentaje Histórico (%)')
    for i, v in enumerate(est_dist): plt.text(v + 1, i, f"{v:.1f}%", color='#8e44ad', va='center', fontweight='bold')
    plt.tight_layout(); plt.savefig('grafico_estudios.png', dpi=300); plt.close()

# --- 3. CLASE MAESTRA DE REPORTE PDF (FPDF) ---
class ReporteIntegral(FPDF):
    def header(self):
        # Evitar encabezado en la portada (página 1)
        if self.page_no() > 1:
            self.set_font('Arial', 'B', 10)
            self.set_text_color(150, 150, 150)
            self.cell(0, 5, 'PARACEL - MONITOREO DE IMPACTO SOCIAL (2022-2026)', 0, 1, 'R')
            self.line(10, 16, 200, 16)
            self.ln(5)

    def footer(self):
        # Evitar pie de página en la portada
        if self.page_no() > 1:
            self.set_y(-15)
            self.set_font('Arial', 'I', 8)
            self.set_text_color(128, 128, 128)
            self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'C')

    def txt_clean(self, text):
        return text.replace('ó', 'o').replace('í','i').replace('á','a').replace('é','e').replace('ú','u').replace('ñ','n').replace('ó', 'o').replace('Ó','O').replace('É', 'E')

    def chapter_title(self, label):
        self.set_font('Arial', 'B', 14)
        self.set_text_color(255, 255, 255) # Texto Blanco
        self.set_fill_color(0, 75, 43)     # Fondo Verde Paracel
        self.cell(0, 10, self.txt_clean(label), 0, 1, 'L', 1)
        self.ln(4)

    def heading_sub(self, label):
        self.set_font('Arial', 'B', 12)
        self.set_text_color(0, 75, 43)
        self.cell(0, 8, self.txt_clean(label), 0, 1, 'L')
        self.ln(1)

    def chapter_body(self, text):
        self.set_font('Arial', '', 11)
        self.set_text_color(60, 60, 60)
        self.multi_cell(0, 6, self.txt_clean(text))
        self.ln(3)

def ensamblar_pdf(df):
    pdf = ReporteIntegral()
    
    # --- PORTADA ---
    pdf.add_page()
    if os.path.exists(logo_path):
        # Centrar logo en el tercio superior
        pdf.image(logo_path, x=65, y=40, w=80)
    pdf.set_y(110)
    pdf.set_font('Arial', 'B', 24)
    pdf.set_text_color(0, 75, 43)
    pdf.cell(0, 15, pdf.txt_clean('REPORTE INTEGRAL EJECUTIVO'), 0, 1, 'C')
    pdf.set_font('Arial', '', 16)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 10, pdf.txt_clean('Estudio Longitudinal de Percepción e Impacto Social'), 0, 1, 'C')
    pdf.ln(20)
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 6, 'Consolidado Histórico: 2022 - 2025', 0, 1, 'C')
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(0, 15, f'Total Panel Enuestado: {len(df)} registros validados', 0, 1, 'C')
    
    # --- CAPÍTULO 1: METODOLOGÍA Y GESTIÓN DE DATOS ---
    pdf.add_page()
    pdf.chapter_title('CAPITULO 1: GESTION DE DATOS Y METODOLOGIA')
    
    pdf.heading_sub('1.1 Unificacion Arquitectonica (2022-2025)')
    txt_metodo1 = ("El presente informe reposa sobre el procesamiento cientifico de la 'Base Maestra Limpia' "
                   "generada dinamicamente por algoritmos de ingenieria de datos. Se compilo y armonizo la "
                   "nomenclatura dispersa de 4 periodos corporativos (2022, 2023, 2024, y 2025) bajo una arquitectura "
                   "tabular singular, eliminando sesgos ortograficos y depurando variables invalidas.")
    pdf.chapter_body(txt_metodo1)
    
    pdf.heading_sub('1.2 Imputacion y Rastreo Longitudinal (FFILL / BFILL)')
    txt_metodo2 = ("Para sostener un rigor investigativo a nivel panel, el ecosistema de procesamiento identifico a "
                   "los individuos a traves de una celula identitaria unica (ID anonimizado basado en huella string). "
                   "Esto permitio que atributos estaticos omitidos por el encuestado (Genero, Edad, Sector) en "
                   "algunos de sus años fuesen reconstruidos (imputados direccionalmente) tomando como referencia "
                   "sus memorias perifericas.")
    pdf.chapter_body(txt_metodo2)

    pdf.heading_sub('1.3 Motor de Inferencia Perceptivo (Logica de Exclusión)')
    txt_metodo3 = ("Una taxonomia rigurosa dicta el dictamen de Aprobacion Positiva, Neutra o Negativa. "
                   "En primer limite, toda persona que afirme 'No ver ningun aspecto positivo' a lo largo del "
                   "cuestionario abierto, es categorizada matematicamente como No Positiva (Negacion Logica). A la inversa, "
                   "toda asociacion positiva valida (ej: Trabajo, Camino, Beneficio, Comercial) califica "
                   "la apreciacion hacia la fabrica bajo un escudo de APROBACION POSITIVA.")
    pdf.chapter_body(txt_metodo3)

    # --- CAPÍTULO 2: PERFIL SOCIODEMOGRÁFICO ---
    pdf.add_page()
    pdf.chapter_title('CAPITULO 2: PERFIL SOCIODEMOGRAFICO DEL PANEL')
    txt_dem = ("En este segmento se transparenta la integracion cultural, etarea y de riquezas de las "
               "comunidades aledañas involucradas en el entorno de influencia del polo industrial Paracel.")
    pdf.chapter_body(txt_dem)
    
    if os.path.exists('grafico_demografia.png'):
        pdf.image('grafico_demografia.png', x=15, w=180); pdf.ln(5)
    
    txt_dem2 = ("Mediante algoritmos de normalizacion, el Nivel Socioeconomico (Originalmente reportado en clasificaciones "
                "de marketing tales como C1, C2, D, E) y los Niveles de Estudio (Básica, Tecnicatura, Doctor) se transcribieron "
                "a polos semanticos universales (Alto, Medio, Bajo / Superior, Secundaria, Primaria) para evitar "
                "dilucion de tendencias por sobre-categorias.")
    pdf.chapter_body(txt_dem2)
    
    if os.path.exists('grafico_estudios.png'):
        pdf.image('grafico_estudios.png', x=30, w=150)
        
    # --- CAPITULO 3: HALLAZGOS DE PERCEPCIÓN E IMPACTO ---
    pdf.add_page()
    pdf.chapter_title('CAPITULO 3: COMPRENSION CLAVE Y ACEPTACION SOCIAL')
    
    pct_25 = "N/D"
    df25 = df[df['año'] == 2025]
    if not df25.empty:
        counts = df25['percepcion_final'].value_counts(normalize=True)*100
        if 'Positiva' in counts: pct_25 = f"{counts['Positiva']:.1f}%"

    txt_perc = (f"El diagnostico termico del año 2025 proyecta un {pct_25} de Positividad general hacia el proyecto Paracel "
                "a nivel comunal (Licencia Social para operar vigente). El grafico a continuacion "
                "ejemplifica el valle historico, derivado mayormente de los temores medioambientales y financieros "
                "de los ultimos trimestres publicos.")
    pdf.chapter_body(txt_perc)
    
    if os.path.exists('grafico_kpi_tendencia.png'):
        pdf.image('grafico_kpi_tendencia.png', x=10, w=190); pdf.ln(5)
        
    pdf.heading_sub('Tension Territorial y Desglose por Distrito')
    txt_mapa = ("Es absolutamente clave observar que las localidades y distritos leen las oportunidades y crisis de "
                "Paracel desde angulos drasticamente diferentes. Los encuestados en el centro urbano acusan mayor "
                "riesgo comunicacional, frente a periferias con expectativas altas de empleo directo.")
    pdf.chapter_body(txt_mapa)
    
    if os.path.exists('grafico_mapa_comunas.png'):
        pdf.image('grafico_mapa_comunas.png', x=15, w=180); pdf.ln(2)

    # --- CAPITULO 4: RELATO CORPORATIVO Y CONTEXTO
    pdf.add_page()
    pdf.chapter_title('CAPITULO 4: CRONOGRAMA CORPORATIVO / EFECTOS EN EL CAMPO')
    
    txt_corp = ("La aceptacion o denegacion comunitaria no ocurre en el vacio tecnico. Los datos de "
                "positividad responden milimetricamente a los Hitos y Crisis que la Corporacion afronta "
                "en la esfera de la opinion publica y su inversion tangible:")
    pdf.chapter_body(txt_corp)
    
    hitos = ("AÑO 2022 - FASE ESTRATEGICA Y PLANIFICACION\n"
             "- Positivos: Entrada de Heinzel Holding y obtencion de Licencias Gubernamentales.\n"
             "- Criticos: Planificacion pasiva bajo rigidos Estandares IFC. Impacto intangible en economia vecinal.\n\n"
             "AÑO 2023 - FASE INDUSTRIAL VISIBLE\n"
             "- Positivos: Botadura visible de barcazas portuarias y asuncion de nueva cupula gerencial (CEO).\n"
             "- Criticos: Relevo del movimiento obrero temprano de constructoras locales.\n\n"
             "AÑO 2024 - PICO DE PROSPERIDAD DIRECTA\n"
             "- Positivos: Record oficial de empleo directo vivo (1.800 colaboradores) y 67.000 Ha productivas de bosque plantado en pie.\n"
             "- Criticos: Primeros atisbos de rediseño logistico por el mercado cambiario.\n\n"
             "AÑO 2025 - VALLE DE CONTRACCION CRITICA\n"
             "- Positivos: Reactivacion a traves del nuevo acuerdo logistico de revision integral (BID Invest).\n"
             "- Criticos: Retiro de empresas satelites, ralentizacion operativa temporal y despido escalonado de cuadrillas sociales afectando severamente el tejido esperanzador del polo Norte.")
    pdf.chapter_body(hitos)

    pdf.output(output_name)
    print(f"[{output_name}] compilado exitosamente.")

if __name__ == "__main__":
    print("Iniciando Sistema de Reporte Documental...")
    print("Ingestando Datos Maestros...")
    df = pd.read_excel(file_path_limpia)
    print("Renderizando Cartografia Analitica...")
    crear_graficos(df)
    print("Mapeando PDF a traves de FPDF...")
    ensamblar_pdf(df)
    
    # Limpieza de imágenes temporales
    for file in os.listdir():
        if file.startswith('grafico_') and file.endswith('.png'):
            try: os.remove(file)
            except: pass
    
    print("Reporte Listo.")
