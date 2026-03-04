import os
import re
import math
import shutil
import tempfile
import unicodedata
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter
from fpdf import FPDF


# =========================================================
# 1. CONFIGURACION GENERAL
# =========================================================

@dataclass
class Config:
    dir_path: str = r"C:\Users\DiegoMeza\OneDrive - PARACEL S.A\MONITOREO_IMPACTO_SOCIAL_PARACEL\NAUTA PERCEPCIÓN INFORMES\encuesta_percepcion_2026"
    file_name: str = "BASE_CONSOLIDADA_SERIES_LIMPIA.xlsx"
    logo_name: str = "LOGO_PARACEL_SINFONDO.png"
    output_name: str = "Reporte_Integral_Impacto_Social_2026.pdf"
    min_muestra_comunidad: int = 8
    top_n_comunidades: int = 12

    @property
    def file_path(self) -> str:
        return os.path.join(self.dir_path, self.file_name)

    @property
    def logo_path(self) -> str:
        return os.path.join(os.path.dirname(self.dir_path), self.logo_name)

    @property
    def output_path(self) -> str:
        return os.path.join(self.dir_path, self.output_name)


CFG = Config()


# =========================================================
# 2. UTILIDADES GENERALES
# =========================================================

def ascii_text(value) -> str:
    if value is None:
        return ""
    text = str(value)
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def normalize_key(text: str) -> str:
    text = ascii_text(text).lower()
    text = re.sub(r"[^a-z0-9]+", "", text)
    return text


def safe_pct(num: float, den: float, ndigits: int = 1) -> float:
    if den in (0, None) or pd.isna(den):
        return 0.0
    return round((num / den) * 100, ndigits)


def truncate(text: str, width: int = 38) -> str:
    text = ascii_text(text)
    return text if len(text) <= width else text[: width - 3] + "..."


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def infer_column(df: pd.DataFrame, aliases: List[str]) -> Optional[str]:
    norm_map = {normalize_key(col): col for col in df.columns}
    for alias in aliases:
        key = normalize_key(alias)
        if key in norm_map:
            return norm_map[key]
    return None


def add_missing_columns(df: pd.DataFrame, cols: List[str]) -> pd.DataFrame:
    for col in cols:
        if col not in df.columns:
            df[col] = np.nan
    return df


# =========================================================
# 3. CARGA, LIMPIEZA Y ESTANDARIZACION
# =========================================================

def cargar_y_preparar_datos(file_path: str) -> pd.DataFrame:
    df = pd.read_excel(file_path)

    df.columns = [ascii_text(c) for c in df.columns]

    colmap = {}

    year_col = infer_column(df, ["año", "ano", "year", "periodo", "ejercicio"])
    percep_col = infer_column(df, ["percepcion_final", "percepcion", "clasificacion_percepcion", "sentimiento"])
    comunidad_col = infer_column(df, ["comunidad", "distrito", "localidad", "barrio", "zona"])
    genero_col = infer_column(df, ["genero", "sexo"])
    nse_col = infer_column(df, ["nse", "nivel_socioeconomico", "estrato", "segmento_socioeconomico"])
    estudios_col = infer_column(df, ["estudios", "nivel_educativo", "escolaridad", "instruccion"])

    if year_col:
        colmap[year_col] = "año"
    if percep_col:
        colmap[percep_col] = "percepcion_final"
    if comunidad_col:
        colmap[comunidad_col] = "comunidad"
    if genero_col:
        colmap[genero_col] = "género"
    if nse_col:
        colmap[nse_col] = "nse"
    if estudios_col:
        colmap[estudios_col] = "estudios"

    df = df.rename(columns=colmap)
    df = add_missing_columns(df, ["año", "percepcion_final", "comunidad", "género", "nse", "estudios"])

    # Año
    df["año"] = (
        df["año"]
        .astype(str)
        .str.extract(r"(\d{4})", expand=False)
    )
    df["año"] = pd.to_numeric(df["año"], errors="coerce").astype("Int64")

    # Limpieza de categoricas
    for col in ["percepcion_final", "comunidad", "género", "nse", "estudios"]:
        df[col] = df[col].astype(str).replace({"nan": np.nan, "None": np.nan, "": np.nan})
        df[col] = df[col].map(lambda x: ascii_text(x) if pd.notna(x) else np.nan)

    df["percepcion_final"] = df["percepcion_final"].map(normalizar_percepcion)
    df["género"] = df["género"].map(normalizar_genero)
    df["nse"] = df["nse"].map(normalizar_nse)
    df["estudios"] = df["estudios"].map(normalizar_estudios)
    df["comunidad"] = df["comunidad"].map(normalizar_comunidad)

    # Eliminar filas completamente vacias en variables clave
    df = df[~(df["año"].isna() & df["percepcion_final"].isna() & df["comunidad"].isna())].copy()

    return df.reset_index(drop=True)


def normalizar_percepcion(x: Optional[str]) -> Optional[str]:
    if pd.isna(x):
        return np.nan
    s = normalize_key(x)

    positivos = [
        "positiva", "positivo", "aprobacion", "aprueba", "favorable",
        "favor", "buena", "bien", "acepta", "aceptacion"
    ]
    negativos = [
        "negativa", "negativo", "desaprobacion", "rechazo", "desfavorable",
        "mala", "mal", "critica", "oposicion"
    ]
    neutros = [
        "neutra", "neutro", "indiferente", "regular", "nsnr",
        "nosabe", "nosabe/noresponde", "noopina"
    ]

    if any(t in s for t in positivos):
        return "Positiva"
    if any(t in s for t in negativos):
        return "Negativa"
    if any(t in s for t in neutros):
        return "Neutra"

    original = ascii_text(x).strip().title()
    if original in {"Positiva", "Negativa", "Neutra"}:
        return original

    return original if original else np.nan


def normalizar_genero(x: Optional[str]) -> Optional[str]:
    if pd.isna(x):
        return np.nan
    s = normalize_key(x)
    if s in {"f", "femenino", "mujer", "female"}:
        return "Mujer"
    if s in {"m", "masculino", "hombre", "male"}:
        return "Hombre"
    if s in {"otro", "nobinario", "nobinaria", "noresponde"}:
        return "Otro / No declara"
    return ascii_text(x).title()


def normalizar_nse(x: Optional[str]) -> Optional[str]:
    if pd.isna(x):
        return np.nan
    s = normalize_key(x)
    if s in {"a", "ab", "abc1", "c1", "alto"}:
        return "Alto"
    if s in {"c2", "c3", "medio", "mediobajo", "mediomedio", "mediotipico"}:
        return "Medio"
    if s in {"d", "e", "bajo", "muybajo"}:
        return "Bajo"
    return ascii_text(x).title()


def normalizar_estudios(x: Optional[str]) -> Optional[str]:
    if pd.isna(x):
        return np.nan
    s = normalize_key(x)

    if any(t in s for t in ["sinestudio", "sininstruccion", "ninguno"]):
        return "Sin instruccion"
    if any(t in s for t in ["primaria", "basica", "escolarbasica"]):
        return "Primaria / Basica"
    if any(t in s for t in ["secundaria", "media", "bachiller"]):
        return "Secundaria / Media"
    if any(t in s for t in ["tecnico", "tecnicatura"]):
        return "Tecnica"
    if any(t in s for t in ["universitaria", "superior", "grado", "licenciatura", "ingenieria"]):
        return "Superior"
    if any(t in s for t in ["maestria", "doctorado", "postgrado", "especializacion"]):
        return "Posgrado"

    return ascii_text(x).title()


def normalizar_comunidad(x: Optional[str]) -> Optional[str]:
    if pd.isna(x):
        return np.nan
    s = ascii_text(x).strip()
    s = re.sub(r"\s+", " ", s)
    return s.title()


# =========================================================
# 4. INDICADORES Y TABLAS ANALITICAS
# =========================================================

def construir_tabla_anual(df: pd.DataFrame) -> pd.DataFrame:
    base = df.dropna(subset=["año", "percepcion_final"]).copy()

    tab = pd.crosstab(base["año"], base["percepcion_final"])
    for col in ["Positiva", "Neutra", "Negativa"]:
        if col not in tab.columns:
            tab[col] = 0

    tab = tab[["Positiva", "Neutra", "Negativa"]].sort_index()
    tab["Total"] = tab.sum(axis=1)
    tab["Positiva_%"] = np.where(tab["Total"] > 0, tab["Positiva"] / tab["Total"] * 100, 0)
    tab["Negativa_%"] = np.where(tab["Total"] > 0, tab["Negativa"] / tab["Total"] * 100, 0)
    tab["Balance_neto_pp"] = tab["Positiva_%"] - tab["Negativa_%"]
    tab["Var_Pos_pp_vs_prev"] = tab["Positiva_%"].diff()

    return tab.reset_index()


def construir_tabla_comunidades(df: pd.DataFrame, min_muestra: int = 8) -> pd.DataFrame:
    dfv = df.dropna(subset=["año", "comunidad", "percepcion_final"]).copy()
    if dfv.empty:
        return pd.DataFrame(columns=["año", "comunidad", "n", "positiva", "neutra", "negativa", "positiva_%", "balance_neto_pp"])

    ultimo_año = int(dfv["año"].dropna().max())
    dfx = dfv[dfv["año"] == ultimo_año].copy()

    grp = dfx.groupby(["comunidad", "percepcion_final"]).size().unstack(fill_value=0)
    for col in ["Positiva", "Neutra", "Negativa"]:
        if col not in grp.columns:
            grp[col] = 0

    grp["n"] = grp.sum(axis=1)
    grp = grp[grp["n"] >= min_muestra].copy()

    if grp.empty:
        return pd.DataFrame(columns=["año", "comunidad", "n", "positiva", "neutra", "negativa", "positiva_%", "balance_neto_pp"])

    grp["positiva_%"] = grp["Positiva"] / grp["n"] * 100
    grp["negativa_%"] = grp["Negativa"] / grp["n"] * 100
    grp["balance_neto_pp"] = grp["positiva_%"] - grp["negativa_%"]

    out = grp.reset_index().rename(columns={
        "Positiva": "positiva",
        "Neutra": "neutra",
        "Negativa": "negativa"
    })
    out.insert(0, "año", ultimo_año)
    out = out.sort_values(["positiva_%", "n"], ascending=[False, False]).reset_index(drop=True)
    return out


def construir_distribucion(df: pd.DataFrame, col: str) -> pd.DataFrame:
    ser = df[col].dropna()
    if ser.empty:
        return pd.DataFrame(columns=[col, "n", "%"])
    out = ser.value_counts(dropna=True).rename_axis(col).reset_index(name="n")
    out["%"] = out["n"] / out["n"].sum() * 100
    return out


def metricas_calidad(df: pd.DataFrame) -> Dict[str, float]:
    cols = ["año", "percepcion_final", "comunidad", "género", "nse", "estudios"]
    comp = {col: round(df[col].notna().mean() * 100, 1) for col in cols}
    comp["integridad_promedio_%"] = round(np.mean(list(comp.values())), 1)
    comp["registros"] = int(len(df))
    comp["años_cubiertos"] = int(df["año"].dropna().nunique()) if df["año"].notna().any() else 0
    comp["comunidades"] = int(df["comunidad"].dropna().nunique()) if df["comunidad"].notna().any() else 0
    return comp


def construir_resumen_ejecutivo(df: pd.DataFrame) -> Dict[str, object]:
    anuales = construir_tabla_anual(df)
    calidad = metricas_calidad(df)
    comunidades = construir_tabla_comunidades(df, CFG.min_muestra_comunidad)

    ultimo_año = None
    positividad_ultimo = 0.0
    balance_ultimo = 0.0
    delta_vs_prev = np.nan
    muestra_ultimo = 0

    if not anuales.empty:
        fila = anuales.iloc[-1]
        ultimo_año = int(fila["año"])
        positividad_ultimo = float(fila["Positiva_%"])
        balance_ultimo = float(fila["Balance_neto_pp"])
        delta_vs_prev = float(fila["Var_Pos_pp_vs_prev"]) if pd.notna(fila["Var_Pos_pp_vs_prev"]) else np.nan
        muestra_ultimo = int(fila["Total"])

    mejor_comunidad = None
    peor_comunidad = None

    if not comunidades.empty:
        mejor = comunidades.sort_values(["positiva_%", "n"], ascending=[False, False]).iloc[0]
        peor = comunidades.sort_values(["positiva_%", "n"], ascending=[True, False]).iloc[0]
        mejor_comunidad = {
            "comunidad": mejor["comunidad"],
            "positiva_%": round(float(mejor["positiva_%"]), 1),
            "n": int(mejor["n"])
        }
        peor_comunidad = {
            "comunidad": peor["comunidad"],
            "positiva_%": round(float(peor["positiva_%"]), 1),
            "n": int(peor["n"])
        }

    return {
        "anuales": anuales,
        "comunidades": comunidades,
        "dist_genero": construir_distribucion(df, "género"),
        "dist_nse": construir_distribucion(df, "nse"),
        "dist_estudios": construir_distribucion(df, "estudios"),
        "calidad": calidad,
        "ultimo_año": ultimo_año,
        "positividad_ultimo": round(positividad_ultimo, 1),
        "balance_ultimo": round(balance_ultimo, 1),
        "delta_vs_prev": round(delta_vs_prev, 1) if pd.notna(delta_vs_prev) else np.nan,
        "muestra_ultimo": muestra_ultimo,
        "mejor_comunidad": mejor_comunidad,
        "peor_comunidad": peor_comunidad,
    }


# =========================================================
# 5. GRAFICOS
# =========================================================

def configurar_estilo_graficos() -> None:
    plt.rcParams.update({
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "axes.edgecolor": "#D9D9D9",
        "axes.titleweight": "bold",
        "axes.titlesize": 13,
        "axes.labelsize": 10.5,
        "xtick.labelsize": 9.5,
        "ytick.labelsize": 9.5,
        "grid.color": "#EAEAEA",
        "grid.linestyle": "-",
        "grid.linewidth": 0.8,
        "font.family": "DejaVu Sans"
    })


def crear_graficos(df: pd.DataFrame, resumen: Dict[str, object], out_dir: str) -> Dict[str, str]:
    configurar_estilo_graficos()
    ensure_dir(out_dir)

    archivos = {}

    anuales = resumen["anuales"]
    comunidades = resumen["comunidades"]
    dist_genero = resumen["dist_genero"]
    dist_nse = resumen["dist_nse"]
    dist_estudios = resumen["dist_estudios"]

    # 1. Tendencia de positividad
    if not anuales.empty:
        path = os.path.join(out_dir, "grafico_tendencia_positividad.png")
        fig, ax = plt.subplots(figsize=(10.8, 4.6))
        ax.plot(anuales["año"], anuales["Positiva_%"], marker="o", linewidth=2.8, color="#0B6B4B")
        ax.fill_between(anuales["año"], anuales["Positiva_%"], alpha=0.12, color="#0B6B4B")
        ax.axhline(50, linestyle="--", linewidth=1, color="#9E9E9E")
        ax.set_title("Evolucion anual de la percepcion positiva")
        ax.set_xlabel("Año")
        ax.set_ylabel("Positividad (%)")
        ax.yaxis.set_major_formatter(PercentFormatter())
        ymax = max(60, math.ceil(anuales["Positiva_%"].max() / 10) * 10 + 10)
        ax.set_ylim(0, ymax)
        for x, y in zip(anuales["año"], anuales["Positiva_%"]):
            ax.annotate(f"{y:.1f}%", (x, y), textcoords="offset points", xytext=(0, 8), ha="center", fontsize=9, fontweight="bold")
        ax.grid(axis="y")
        fig.tight_layout()
        fig.savefig(path, dpi=300, bbox_inches="tight")
        plt.close(fig)
        archivos["tendencia"] = path

    # 2. Composicion anual de percepcion
    if not anuales.empty:
        path = os.path.join(out_dir, "grafico_composicion_anual.png")
        fig, ax = plt.subplots(figsize=(10.8, 4.8))
        x = np.arange(len(anuales))
        ax.bar(x, anuales["Positiva_%"], label="Positiva", color="#0B6B4B")
        ax.bar(x, anuales["Negativa_%"], bottom=anuales["Positiva_%"], label="Negativa", color="#B23A48")
        restante = 100 - anuales["Positiva_%"] - anuales["Negativa_%"]
        restante = np.where(restante < 0, 0, restante)
        ax.bar(x, restante, bottom=anuales["Positiva_%"] + anuales["Negativa_%"], label="Neutra / otras", color="#C9C9C9")
        ax.set_xticks(x)
        ax.set_xticklabels(anuales["año"].astype(str))
        ax.set_ylim(0, 100)
        ax.set_ylabel("Distribucion porcentual")
        ax.yaxis.set_major_formatter(PercentFormatter())
        ax.set_title("Composicion anual de la percepcion")
        ax.legend(frameon=False, ncol=3, loc="upper center", bbox_to_anchor=(0.5, 1.12))
        fig.tight_layout()
        fig.savefig(path, dpi=300, bbox_inches="tight")
        plt.close(fig)
        archivos["composicion"] = path

    # 3. Comunidades, ultimo año
    if not comunidades.empty:
        plot_df = comunidades.head(CFG.top_n_comunidades).sort_values("positiva_%")
        path = os.path.join(out_dir, "grafico_comunidades_ultimo_ano.png")
        fig, ax = plt.subplots(figsize=(10.8, 6.0))
        colors = np.where(plot_df["positiva_%"] >= 50, "#0B6B4B", "#B23A48")
        ax.barh(plot_df["comunidad"].map(lambda x: truncate(x, 28)), plot_df["positiva_%"], color=colors)
        ax.set_title(f"Positividad por comunidad, ultimo año con muestra >= {CFG.min_muestra_comunidad}")
        ax.set_xlabel("Positividad (%)")
        ax.xaxis.set_major_formatter(PercentFormatter())
        ax.set_xlim(0, 100)
        for i, (v, n) in enumerate(zip(plot_df["positiva_%"], plot_df["n"])):
            ax.text(v + 1.3, i, f"{v:.1f}%  (n={int(n)})", va="center", fontsize=8.8)
        fig.tight_layout()
        fig.savefig(path, dpi=300, bbox_inches="tight")
        plt.close(fig)
        archivos["comunidades"] = path

    # 4. Genero
    if not dist_genero.empty:
        path = os.path.join(out_dir, "grafico_genero.png")
        fig, ax = plt.subplots(figsize=(7.6, 4.2))
        ax.bar(dist_genero["género"].map(lambda x: truncate(x, 22)), dist_genero["%"], color="#2E86AB")
        ax.set_title("Distribucion del panel por genero")
        ax.set_ylabel("Participacion (%)")
        ax.yaxis.set_major_formatter(PercentFormatter())
        for i, v in enumerate(dist_genero["%"]):
            ax.text(i, v + 1.3, f"{v:.1f}%", ha="center", fontsize=9)
        fig.tight_layout()
        fig.savefig(path, dpi=300, bbox_inches="tight")
        plt.close(fig)
        archivos["genero"] = path

    # 5. NSE
    if not dist_nse.empty:
        path = os.path.join(out_dir, "grafico_nse.png")
        fig, ax = plt.subplots(figsize=(7.6, 4.2))
        ax.bar(dist_nse["nse"].map(lambda x: truncate(x, 22)), dist_nse["%"], color="#D98E04")
        ax.set_title("Distribucion del panel por nivel socioeconomico")
        ax.set_ylabel("Participacion (%)")
        ax.yaxis.set_major_formatter(PercentFormatter())
        for i, v in enumerate(dist_nse["%"]):
            ax.text(i, v + 1.3, f"{v:.1f}%", ha="center", fontsize=9)
        fig.tight_layout()
        fig.savefig(path, dpi=300, bbox_inches="tight")
        plt.close(fig)
        archivos["nse"] = path

    # 6. Estudios
    if not dist_estudios.empty:
        path = os.path.join(out_dir, "grafico_estudios.png")
        plot_df = dist_estudios.sort_values("%")
        fig, ax = plt.subplots(figsize=(9.2, 4.8))
        ax.barh(plot_df["estudios"].map(lambda x: truncate(x, 30)), plot_df["%"], color="#6C5B7B")
        ax.set_title("Distribucion del panel por nivel educativo")
        ax.set_xlabel("Participacion (%)")
        ax.xaxis.set_major_formatter(PercentFormatter())
        for i, v in enumerate(plot_df["%"]):
            ax.text(v + 1.0, i, f"{v:.1f}%", va="center", fontsize=9)
        fig.tight_layout()
        fig.savefig(path, dpi=300, bbox_inches="tight")
        plt.close(fig)
        archivos["estudios"] = path

    return archivos


# =========================================================
# 6. REPORTE PDF
# =========================================================

class ReporteIntegralPDF(FPDF):
    def __init__(self, logo_path: Optional[str] = None):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.logo_path = logo_path
        self.set_auto_page_break(auto=True, margin=16)
        self.alias_nb_pages()

        self.COLOR_VERDE = (11, 107, 75)
        self.COLOR_VERDE_SUAVE = (230, 243, 238)
        self.COLOR_GRIS = (90, 90, 90)
        self.COLOR_GRIS_CLARO = (245, 245, 245)
        self.COLOR_ROJO = (178, 58, 72)
        self.COLOR_NEGRO = (45, 45, 45)

    def header(self):
        if self.page_no() == 1:
            return
        self.set_y(8)
        self.set_font("Arial", "B", 9)
        self.set_text_color(*self.COLOR_GRIS)
        self.cell(0, 5, "PARACEL | Monitoreo de percepcion e impacto social", 0, 0, "R")
        self.ln(7)
        self.set_draw_color(220, 220, 220)
        self.line(10, 16, 200, 16)
        self.ln(4)

    def footer(self):
        if self.page_no() == 1:
            return
        self.set_y(-12)
        self.set_draw_color(220, 220, 220)
        self.line(10, self.get_y() - 2, 200, self.get_y() - 2)
        self.set_font("Arial", "I", 8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 6, f"Pagina {self.page_no()} de {{nb}}", 0, 0, "C")

    def t(self, txt) -> str:
        return ascii_text(txt)

    def portada(self, titulo: str, subtitulo: str, periodo: str, universo: int):
        self.add_page()
        self.set_fill_color(*self.COLOR_VERDE)
        self.rect(0, 0, 210, 297, style="F")

        self.set_fill_color(255, 255, 255)
        self.rect(12, 18, 186, 261, style="F")

        if self.logo_path and os.path.exists(self.logo_path):
            self.image(self.logo_path, x=72, y=28, w=66)

        self.set_xy(18, 108)
        self.set_font("Arial", "B", 22)
        self.set_text_color(*self.COLOR_VERDE)
        self.multi_cell(174, 12, self.t(titulo), 0, "C")

        self.ln(4)
        self.set_font("Arial", "", 14)
        self.set_text_color(90, 90, 90)
        self.multi_cell(174, 8, self.t(subtitulo), 0, "C")

        self.ln(14)
        self.set_font("Arial", "B", 12)
        self.set_text_color(70, 70, 70)
        self.cell(174, 8, self.t(f"Serie historica analizada: {periodo}"), 0, 1, "C")

        self.set_font("Arial", "", 11)
        self.cell(174, 8, self.t(f"Registros procesados y validados: {universo:,}".replace(",", ".")), 0, 1, "C")

        self.set_y(245)
        self.set_font("Arial", "", 10)
        self.set_text_color(120, 120, 120)
        self.multi_cell(
            174,
            6,
            self.t(
                "Documento generado automaticamente a partir de la base consolidada, con control de consistencia, "
                "tablas analiticas y visualizaciones ejecutivas."
            ),
            0,
            "C"
        )

    def section_title(self, text: str):
        self.ln(2)
        self.set_fill_color(*self.COLOR_VERDE)
        self.set_text_color(255, 255, 255)
        self.set_font("Arial", "B", 13)
        self.cell(0, 9, self.t(text), 0, 1, "L", 1)
        self.ln(3)

    def subsection_title(self, text: str):
        self.set_text_color(*self.COLOR_VERDE)
        self.set_font("Arial", "B", 11.5)
        self.cell(0, 7, self.t(text), 0, 1, "L")
        self.ln(1)

    def paragraph(self, text: str, size: float = 10.5):
        self.set_font("Arial", "", size)
        self.set_text_color(*self.COLOR_NEGRO)
        self.multi_cell(0, 6, self.t(text))
        self.ln(1.5)

    def note_box(self, text: str):
        x = self.get_x()
        y = self.get_y()
        self.set_fill_color(*self.COLOR_VERDE_SUAVE)
        self.set_draw_color(210, 230, 221)
        h = 18 + (max(0, len(self.t(text)) - 100) // 75) * 5
        self.rect(x, y, 190, h, style="FD")
        self.set_xy(x + 3, y + 3)
        self.set_font("Arial", "", 10)
        self.set_text_color(*self.COLOR_NEGRO)
        self.multi_cell(184, 5.5, self.t(text))
        self.ln(2)

    def kpi_row(self, cards: List[Tuple[str, str]]):
        x0 = 10
        y0 = self.get_y()
        gap = 4
        card_w = (190 - gap * (len(cards) - 1)) / len(cards)
        card_h = 24

        for i, (value, label) in enumerate(cards):
            x = x0 + i * (card_w + gap)
            self.set_xy(x, y0)
            self.set_fill_color(*self.COLOR_GRIS_CLARO)
            self.set_draw_color(225, 225, 225)
            self.rect(x, y0, card_w, card_h, style="FD")
            self.set_xy(x + 2, y0 + 4)
            self.set_font("Arial", "B", 14)
            self.set_text_color(*self.COLOR_VERDE)
            self.cell(card_w - 4, 6, self.t(value), 0, 2, "C")
            self.set_font("Arial", "", 9)
            self.set_text_color(*self.COLOR_GRIS)
            self.multi_cell(card_w - 4, 4.5, self.t(label), 0, "C")

        self.set_y(y0 + card_h + 4)

    def insert_image(self, path: str, x: float = 12, w: float = 186, h: Optional[float] = None):
        if path and os.path.exists(path):
            self.image(path, x=x, y=self.get_y(), w=w, h=h if h else 0)
            self.ln(3)
            if h:
                self.ln(h)

    def simple_table(self, df: pd.DataFrame, widths: List[float], headers: List[str], align: Optional[List[str]] = None):
        if df.empty:
            self.paragraph("No se dispone de informacion suficiente para esta tabla.")
            return

        align = align or ["L"] * len(headers)

        self.set_fill_color(*self.COLOR_VERDE)
        self.set_text_color(255, 255, 255)
        self.set_font("Arial", "B", 9)

        for head, w in zip(headers, widths):
            self.cell(w, 7, self.t(head), 1, 0, "C", 1)
        self.ln()

        self.set_font("Arial", "", 8.8)
        self.set_text_color(*self.COLOR_NEGRO)

        alt = False
        for _, row in df.iterrows():
            self.set_fill_color(252, 252, 252) if alt else self.set_fill_color(245, 245, 245)
            alt = not alt
            for j, (col, w) in enumerate(zip(df.columns, widths)):
                val = row[col]
                if isinstance(val, float):
                    txt = f"{val:.1f}" if not val.is_integer() else f"{int(val)}"
                else:
                    txt = str(val)
                txt = truncate(txt, max(8, int(w * 1.8)))
                self.cell(w, 6.5, self.t(txt), 1, 0, align[j], 1)
            self.ln()
            if self.get_y() > 265:
                self.add_page()
                self.set_fill_color(*self.COLOR_VERDE)
                self.set_text_color(255, 255, 255)
                self.set_font("Arial", "B", 9)
                for head, w in zip(headers, widths):
                    self.cell(w, 7, self.t(head), 1, 0, "C", 1)
                self.ln()
                self.set_font("Arial", "", 8.8)
                self.set_text_color(*self.COLOR_NEGRO)

        self.ln(3)


# =========================================================
# 7. ENSAMBLAJE NARRATIVO DEL INFORME
# =========================================================

def texto_resumen_ejecutivo(resumen: Dict[str, object]) -> str:
    ultimo = resumen["ultimo_año"]
    pos = resumen["positividad_ultimo"]
    bal = resumen["balance_ultimo"]
    delta = resumen["delta_vs_prev"]
    muestra = resumen["muestra_ultimo"]
    integridad = resumen["calidad"]["integridad_promedio_%"]

    partes = [
        f"El ultimo corte disponible corresponde al año {ultimo}, con una muestra valida de {muestra:,} registros.".replace(",", "."),
        f"La percepcion positiva alcanzo {pos:.1f}% y el balance neto entre positividad y negatividad fue de {bal:.1f} puntos porcentuales.",
        f"El indice promedio de completitud de las variables estructurales analizadas fue de {integridad:.1f}%."
    ]

    if pd.notna(delta):
        sentido = "aumento" if delta >= 0 else "disminucion"
        partes.append(f"Respecto al año previo, la positividad {sentido} en {abs(delta):.1f} puntos porcentuales.")

    if resumen["mejor_comunidad"] is not None and resumen["peor_comunidad"] is not None:
        mc = resumen["mejor_comunidad"]
        pc = resumen["peor_comunidad"]
        partes.append(
            f"En el ultimo año, la comunidad con mejor resultado observado fue {mc['comunidad']} "
            f"({mc['positiva_%']:.1f}% de positividad; n={mc['n']}), mientras que la de menor registro de positividad fue "
            f"{pc['comunidad']} ({pc['positiva_%']:.1f}%; n={pc['n']})."
        )

    return " ".join(partes)


def texto_metodologia(df: pd.DataFrame, resumen: Dict[str, object]) -> str:
    anios = sorted([int(x) for x in df["año"].dropna().unique().tolist()])
    periodo = f"{min(anios)} a {max(anios)}" if anios else "sin periodo definido"
    comunidades = resumen["calidad"]["comunidades"]
    return (
        f"El reporte se construye a partir de una base consolidada de serie historica, depurada y homologada para el periodo {periodo}. "
        f"Se ejecutaron procesos de estandarizacion de nombres de variables, normalizacion de categorias de percepcion, genero, nivel socioeconomico y estudios, "
        f"asi como controles de vacios en variables criticas. El universo analitico comprende {len(df):,} registros y {comunidades:,} comunidades o unidades territoriales identificadas."
    ).replace(",", ".")


def texto_calidad(resumen: Dict[str, object]) -> str:
    cal = resumen["calidad"]
    return (
        f"La calidad estructural de la base fue evaluada mediante tasas de completitud por variable. "
        f"Los niveles de cobertura observados fueron: año {cal['año']:.1f}%, percepcion final {cal['percepcion_final']:.1f}%, "
        f"comunidad {cal['comunidad']:.1f}%, genero {cal['género']:.1f}%, nivel socioeconomico {cal['nse']:.1f}% y estudios {cal['estudios']:.1f}%. "
        f"El promedio global de integridad se ubico en {cal['integridad_promedio_%']:.1f}%."
    )


def recomendaciones_tecnicas(resumen: Dict[str, object]) -> List[str]:
    recs = [
        "Establecer un diccionario unico de categorias para percepcion, genero, NSE, comunidad y estudios, a fin de evitar recodificaciones posteriores.",
        "Incorporar un identificador anonimo persistente por informante, de modo que la serie pueda analizarse como panel real y no solo como cortes repetidos.",
        "Definir umbrales minimos de muestra por comunidad antes de reportar rankings territoriales, para reducir conclusiones inestables.",
        "Separar en la base una fecha exacta de levantamiento, adicional al año, para estudiar estacionalidad, eventos criticos y puntos de inflexion.",
        "Construir un tablero complementario que permita filtrar por año, comunidad, perfil sociodemografico y percepcion, con recalculo inmediato de KPI."
    ]

    if resumen["calidad"]["integridad_promedio_%"] < 85:
        recs.insert(
            0,
            "Priorizar un plan de mejora de calidad de datos, especialmente en variables de perfil y localizacion, antes de profundizar inferencias finas por segmentos."
        )
    return recs


def dataframe_anual_reporte(anuales: pd.DataFrame) -> pd.DataFrame:
    if anuales.empty:
        return anuales
    out = anuales.copy()
    out = out[["año", "Total", "Positiva_%", "Negativa_%", "Balance_neto_pp", "Var_Pos_pp_vs_prev"]].copy()
    out.columns = ["Año", "n", "Positiva %", "Negativa %", "Balance neto", "Var. vs previo"]
    out["n"] = out["n"].astype(int)
    return out


def dataframe_comunidades_reporte(comunidades: pd.DataFrame) -> pd.DataFrame:
    if comunidades.empty:
        return comunidades
    out = comunidades.copy()
    out = out[["comunidad", "n", "positiva_%", "balance_neto_pp"]].head(10)
    out.columns = ["Comunidad", "n", "Positiva %", "Balance neto"]
    out["n"] = out["n"].astype(int)
    return out


def ensamblar_pdf(df: pd.DataFrame, resumen: Dict[str, object], graficos: Dict[str, str], cfg: Config) -> None:
    pdf = ReporteIntegralPDF(logo_path=cfg.logo_path)

    años = sorted(df["año"].dropna().astype(int).unique().tolist()) if df["año"].notna().any() else []
    periodo = f"{min(años)} - {max(años)}" if años else "Sin periodo"

    # Portada
    pdf.portada(
        titulo="Reporte integral ejecutivo",
        subtitulo="Monitoreo longitudinal de percepcion e impacto social",
        periodo=periodo,
        universo=len(df)
    )

    # Resumen ejecutivo
    pdf.add_page()
    pdf.section_title("1. Resumen ejecutivo")
    pdf.paragraph(texto_resumen_ejecutivo(resumen))

    delta = resumen["delta_vs_prev"]
    delta_txt = "N/D" if pd.isna(delta) else f"{delta:+.1f} pp"

    pdf.kpi_row([
        (f"{resumen['positividad_ultimo']:.1f}%", "Positividad en el ultimo año"),
        (f"{resumen['balance_ultimo']:.1f} pp", "Balance neto de percepcion"),
        (delta_txt, "Variacion frente al año previo"),
        (f"{resumen['calidad']['integridad_promedio_%']:.1f}%", "Integridad promedio de la base"),
    ])

    pdf.note_box(
        "Este reporte integra narrativa, metricas, tablas y visualizaciones generadas automaticamente a partir de la base consolidada. "
        "La interpretacion debe considerar el tamano de muestra disponible por año y por comunidad, asi como la completitud observada en variables estructurales."
    )

    # Metodologia
    pdf.section_title("2. Base de datos, homologacion y calidad")
    pdf.subsection_title("2.1 Estructura analitica del insumo")
    pdf.paragraph(texto_metodologia(df, resumen))

    pdf.subsection_title("2.2 Evaluacion de calidad del dato")
    pdf.paragraph(texto_calidad(resumen))

    cal = resumen["calidad"]
    tabla_calidad = pd.DataFrame({
        "Variable": ["Año", "Percepcion final", "Comunidad", "Genero", "NSE", "Estudios", "Promedio"],
        "Completitud %": [
            cal["año"], cal["percepcion_final"], cal["comunidad"],
            cal["género"], cal["nse"], cal["estudios"],
            cal["integridad_promedio_%"]
        ]
    })
    pdf.simple_table(tabla_calidad, widths=[110, 40], headers=["Variable", "Completitud %"], align=["L", "C"])

    # Evolucion anual
    pdf.section_title("3. Evolucion temporal de la percepcion")
    pdf.subsection_title("3.1 Tendencia de la positividad")
    pdf.paragraph(
        "La serie anual permite observar la trayectoria de la aceptacion social del proyecto y sus cambios interanuales. "
        "El indicador principal utilizado es la proporcion de respuestas clasificadas como positivas sobre el total valido de percepciones de cada año."
    )
    if "tendencia" in graficos:
        pdf.insert_image(graficos["tendencia"], x=12, w=186)
        pdf.ln(60)

    pdf.subsection_title("3.2 Composicion anual de respuestas")
    if "composicion" in graficos:
        pdf.insert_image(graficos["composicion"], x=12, w=186)
        pdf.ln(62)

    tabla_anual = dataframe_anual_reporte(resumen["anuales"])
    pdf.simple_table(
        tabla_anual,
        widths=[22, 22, 31, 31, 38, 38],
        headers=["Año", "n", "Positiva %", "Negativa %", "Balance neto", "Var. vs previo"],
        align=["C", "C", "C", "C", "C", "C"]
    )

    # Territorio
    pdf.section_title("4. Analisis territorial del ultimo año")
    pdf.paragraph(
        f"Para el ultimo año disponible, se construyeron indicadores por comunidad considerando solamente aquellas con al menos "
        f"{cfg.min_muestra_comunidad} observaciones validas. Esto permite reducir la volatilidad de tasas calculadas sobre bases muy pequeñas."
    )

    if "comunidades" in graficos:
        pdf.insert_image(graficos["comunidades"], x=12, w=186)
        pdf.ln(76)

    tabla_com = dataframe_comunidades_reporte(resumen["comunidades"])
    pdf.simple_table(
        tabla_com,
        widths=[96, 22, 32, 40],
        headers=["Comunidad", "n", "Positiva %", "Balance neto"],
        align=["L", "C", "C", "C"]
    )

    # Perfil del panel
    pdf.section_title("5. Perfil sociodemografico del panel")
    pdf.paragraph(
        "La composicion del panel se resume mediante la distribucion observada de genero, nivel socioeconomico y nivel educativo. "
        "Estas estructuras son relevantes porque condicionan la interpretacion de la percepcion agregada y ayudan a identificar posibles sesgos de composicion."
    )

    if "genero" in graficos:
        pdf.subsection_title("5.1 Genero")
        pdf.insert_image(graficos["genero"], x=30, w=150)
        pdf.ln(52)

    if "nse" in graficos:
        pdf.subsection_title("5.2 Nivel socioeconomico")
        pdf.insert_image(graficos["nse"], x=30, w=150)
        pdf.ln(52)

    if "estudios" in graficos:
        pdf.subsection_title("5.3 Nivel educativo")
        pdf.insert_image(graficos["estudios"], x=20, w=170)
        pdf.ln(58)

    # Conclusiones
    pdf.section_title("6. Conclusiones y recomendaciones tecnicas")
    pdf.paragraph(
        "En conjunto, la base permite construir una lectura ejecutiva consistente sobre el clima de percepcion alrededor del proyecto, "
        "aunque la precision de algunas desagregaciones depende del volumen efectivo de casos y de la completitud de la informacion estructural."
    )

    for i, rec in enumerate(recomendaciones_tecnicas(resumen), start=1):
        pdf.paragraph(f"{i}. {rec}")

    # Guardado
    pdf.output(cfg.output_path)


# =========================================================
# 8. FLUJO PRINCIPAL
# =========================================================

def main():
    temp_dir = tempfile.mkdtemp(prefix="reporte_percepcion_")
    try:
        df = cargar_y_preparar_datos(CFG.file_path)
        resumen = construir_resumen_ejecutivo(df)
        graficos = crear_graficos(df, resumen, temp_dir)
        ensamblar_pdf(df, resumen, graficos, CFG)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
