import os
import re
import math
import shutil
import tempfile
import unicodedata
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Wedge, Circle
from matplotlib.ticker import PercentFormatter
import PyPDF2
from pdf2docx import Converter
from fpdf import FPDF

# =========================================================
# 1. CONFIGURACION GENERAL
# =========================================================

@dataclass
class Config:
    dir_path: str = r"C:\Users\DiegoMeza\OneDrive - PARACEL S.A\MONITOREO_IMPACTO_SOCIAL_PARACEL\NAUTA PERCEPCIÓN INFORMES\encuesta_percepcion_2026"
    file_name: str = "BASE_CONSOLIDADA_SERIES_LIMPIA.xlsx"
    logo_name: str = "LOGO_PARACEL_SINFONDO.png"
    output_name: str = "Reporte_Integral_Impacto_Social_2026_ULTRA.pdf"

    min_muestra_comunidad: int = 8
    top_n_comunidades: int = 12
    top_n_muestra: int = 10

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
# 2. PALETA Y UTILIDADES GRAFICAS
# =========================================================

PALETTE = {
    "green_900": "#0B3D2E",
    "green_800": "#0F5132",
    "green_700": "#146C43",
    "green_600": "#198754",
    "green_500": "#2E8B57",
    "green_400": "#56A36C",
    "green_300": "#7CBC82",
    "green_200": "#A7D7A9",
    "green_100": "#D8F0D2",
    "green_050": "#EEF8EC",
    "olive": "#7A8E3A",
    "lime": "#A8C66C",
    "mint": "#CDECCF",
    "gray_900": "#2E2E2E",
    "gray_700": "#666666",
    "gray_500": "#9A9A9A",
    "gray_300": "#D9D9D9",
    "gray_200": "#ECECEC",
    "gray_100": "#F7F7F7",
    "white": "#FFFFFF",
    "red_soft": "#C56A6A",
    "amber_soft": "#D7A94B",
}

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

def truncate(text: str, width: int = 40) -> str:
    text = ascii_text(text)
    return text if len(text) <= width else text[:width - 3] + "..."

def safe_pct(num: float, den: float, ndigits: int = 1) -> float:
    if den is None or den == 0 or pd.isna(den):
        return 0.0
    return round((num / den) * 100, ndigits)

def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)

def infer_column(df: pd.DataFrame, aliases: List[str]) -> Optional[str]:
    norm_map = {normalize_key(col): col for col in df.columns}
    for alias in aliases:
        k = normalize_key(alias)
        if k in norm_map:
            return norm_map[k]
    return None

def add_missing_columns(df: pd.DataFrame, cols: List[str]) -> pd.DataFrame:
    for col in cols:
        if col not in df.columns:
            df[col] = np.nan
    return df

def to_int_or_zero(value: Any) -> int:
    if pd.isna(value):
        return 0
    return int(value)

def to_float_or_zero(value: Any) -> float:
    if pd.isna(value):
        return 0.0
    return float(value)

def semaforo_estado(valor: float) -> str:
    if pd.isna(valor):
        return "Sin dato"
    if valor >= 70:
        return "Favorable"
    if valor >= 50:
        return "Atencion"
    return "Critico"

def semaforo_color(valor: float) -> str:
    if pd.isna(valor):
        return PALETTE["gray_500"]
    if valor >= 70:
        return PALETTE["green_700"]
    if valor >= 50:
        return PALETTE["amber_soft"]
    return PALETTE["red_soft"]

def format_num(value: Any, decimals: int = 1, pct: bool = False) -> str:
    if pd.isna(value):
        return "N/D"
    if isinstance(value, (int, np.integer)):
        return f"{int(value):,}".replace(",", ".")
    if isinstance(value, (float, np.floating)):
        txt = f"{value:,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return f"{txt}%" if pct else txt
    return ascii_text(value)

# =========================================================
# 3. ESTILO GENERAL DE GRAFICOS
# =========================================================

def configurar_estilo_graficos() -> None:
    plt.rcParams.update({
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "savefig.facecolor": "white",
        "axes.edgecolor": PALETTE["gray_300"],
        "axes.linewidth": 0.8,
        "axes.titlesize": 13,
        "axes.titleweight": "bold",
        "axes.labelsize": 10.5,
        "xtick.labelsize": 9.3,
        "ytick.labelsize": 9.3,
        "font.family": "DejaVu Sans",
        "grid.color": PALETTE["gray_200"],
        "grid.linestyle": "-",
        "grid.linewidth": 0.8
    })

# =========================================================
# 4. CARGA, LIMPIEZA Y ESTANDARIZACION
# =========================================================

def normalizar_percepcion(x: Optional[str]) -> Optional[str]:
    if pd.isna(x):
        return np.nan
    s = normalize_key(x)

    negativos = [
        "nopositiva", "negativa", "negativo", "desaprobacion", "rechazo",
        "desfavorable", "mala", "mal", "critica", "oposicion", "nopositivo"
    ]
    positivos = [
        "positiva", "positivo", "aprobacion", "aprueba", "favorable",
        "favor", "buena", "bien", "acepta", "aceptacion"
    ]
    neutros = [
        "neutra", "neutro", "indiferente", "regular", "nsnr",
        "nosabe", "noopina", "nosabenoresponde"
    ]

    if any(t in s for t in negativos):
        return "Negativa"
    if any(t in s for t in positivos):
        return "Positiva"
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
    if s in {"otro", "nobinario", "nobinaria", "nodeclara", "noresponde"}:
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

    df["año"] = df["año"].astype(str).str.extract(r"(\d{4})", expand=False)
    df["año"] = pd.to_numeric(df["año"], errors="coerce").astype("Int64")

    for col in ["percepcion_final", "comunidad", "género", "nse", "estudios"]:
        df[col] = df[col].astype(str).replace({"nan": np.nan, "None": np.nan, "": np.nan})
        df[col] = df[col].map(lambda x: ascii_text(x) if pd.notna(x) else np.nan)

    df["percepcion_final"] = df["percepcion_final"].map(normalizar_percepcion)
    df["género"] = df["género"].map(normalizar_genero)
    df["nse"] = df["nse"].map(normalizar_nse)
    df["estudios"] = df["estudios"].map(normalizar_estudios)
    df["comunidad"] = df["comunidad"].map(normalizar_comunidad)

    df = df[~(df["año"].isna() & df["percepcion_final"].isna() & df["comunidad"].isna())].copy()

    if df["año"].notna().any():
        df = df.sort_values(["año", "comunidad"], na_position="last").reset_index(drop=True)

    return df

# =========================================================
# 5. INDICADORES Y TABLAS ANALITICAS
# =========================================================

def construir_tabla_anual(df: pd.DataFrame) -> pd.DataFrame:
    base = df.dropna(subset=["año", "percepcion_final"]).copy()
    if base.empty:
        return pd.DataFrame(columns=[
            "año", "Positiva", "Neutra", "Negativa", "Total",
            "Positiva_%", "Negativa_%", "Neutra_%", "Balance_neto_pp",
            "Var_Pos_pp_vs_prev"
        ])

    tab = pd.crosstab(base["año"], base["percepcion_final"])
    for col in ["Positiva", "Neutra", "Negativa"]:
        if col not in tab.columns:
            tab[col] = 0

    tab = tab[["Positiva", "Neutra", "Negativa"]].sort_index()
    tab["Total"] = tab.sum(axis=1)
    tab["Positiva_%"] = np.where(tab["Total"] > 0, tab["Positiva"] / tab["Total"] * 100, 0)
    tab["Negativa_%"] = np.where(tab["Total"] > 0, tab["Negativa"] / tab["Total"] * 100, 0)
    tab["Neutra_%"] = np.where(tab["Total"] > 0, tab["Neutra"] / tab["Total"] * 100, 0)
    tab["Balance_neto_pp"] = tab["Positiva_%"] - tab["Negativa_%"]
    tab["Var_Pos_pp_vs_prev"] = tab["Positiva_%"].diff()

    return tab.reset_index()


def construir_tabla_comunidades(df: pd.DataFrame, min_muestra: int = 8) -> pd.DataFrame:
    base = df.dropna(subset=["año", "comunidad", "percepcion_final"]).copy()
    if base.empty:
        return pd.DataFrame(columns=[
            "año", "comunidad", "positiva", "neutra", "negativa",
            "n", "positiva_%", "negativa_%", "neutra_%", "balance_neto_pp"
        ])

    ultimo_año = int(base["año"].dropna().max())
    dfx = base[base["año"] == ultimo_año].copy()

    grp = dfx.groupby(["comunidad", "percepcion_final"]).size().unstack(fill_value=0)
    for col in ["Positiva", "Neutra", "Negativa"]:
        if col not in grp.columns:
            grp[col] = 0

    grp["n"] = grp.sum(axis=1)
    grp = grp[grp["n"] >= min_muestra].copy()

    if grp.empty:
        return pd.DataFrame(columns=[
            "año", "comunidad", "positiva", "neutra", "negativa",
            "n", "positiva_%", "negativa_%", "neutra_%", "balance_neto_pp"
        ])

    grp["positiva_%"] = grp["Positiva"] / grp["n"] * 100
    grp["negativa_%"] = grp["Negativa"] / grp["n"] * 100
    grp["neutra_%"] = grp["Neutra"] / grp["n"] * 100
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
    return out.sort_values("%", ascending=False).reset_index(drop=True)


def matriz_calidad_por_año(df: pd.DataFrame, cols: List[str]) -> pd.DataFrame:
    base = df.copy()
    if base["año"].isna().all():
        return pd.DataFrame()

    out = base.groupby("año")[cols].apply(lambda x: x.notna().mean() * 100)
    return out.round(1).sort_index()


def calcular_indices_avanzados(df: pd.DataFrame, anuales: pd.DataFrame, comunidades: pd.DataFrame) -> Dict[str, Any]:
    integridad = metricas_calidad(df)
    ultimo_año = int(anuales["año"].max()) if not anuales.empty else None

    positividad_ultimo = float(anuales.iloc[-1]["Positiva_%"]) if not anuales.empty else np.nan
    negativa_ultimo = float(anuales.iloc[-1]["Negativa_%"]) if not anuales.empty else np.nan
    balance_ultimo = float(anuales.iloc[-1]["Balance_neto_pp"]) if not anuales.empty else np.nan
    muestra_ultimo = int(anuales.iloc[-1]["Total"]) if not anuales.empty else 0
    delta_vs_prev = float(anuales.iloc[-1]["Var_Pos_pp_vs_prev"]) if (not anuales.empty and pd.notna(anuales.iloc[-1]["Var_Pos_pp_vs_prev"])) else np.nan

    volatilidad = float(anuales["Positiva_%"].std(ddof=0)) if len(anuales) > 1 else 0.0
    mejor_anio = int(anuales.loc[anuales["Positiva_%"].idxmax(), "año"]) if not anuales.empty else None
    peor_anio = int(anuales.loc[anuales["Positiva_%"].idxmin(), "año"]) if not anuales.empty else None

    cobertura_territorial = int(df["comunidad"].dropna().nunique()) if df["comunidad"].notna().any() else 0

    concentracion_muestra = np.nan
    comunidad_mayor_n = None
    if not comunidades.empty:
        comunidad_mayor = comunidades.sort_values("n", ascending=False).iloc[0]
        comunidad_mayor_n = comunidad_mayor["comunidad"]
        concentracion_muestra = float(comunidad_mayor["n"] / comunidades["n"].sum() * 100)

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
        "calidad": integridad,
        "ultimo_año": ultimo_año,
        "positividad_ultimo": round(positividad_ultimo, 1) if not pd.isna(positividad_ultimo) else np.nan,
        "negativa_ultimo": round(negativa_ultimo, 1) if not pd.isna(negativa_ultimo) else np.nan,
        "balance_ultimo": round(balance_ultimo, 1) if not pd.isna(balance_ultimo) else np.nan,
        "muestra_ultimo": muestra_ultimo,
        "delta_vs_prev": round(delta_vs_prev, 1) if not pd.isna(delta_vs_prev) else np.nan,
        "volatilidad_positividad": round(volatilidad, 1),
        "mejor_año": mejor_anio,
        "peor_año": peor_anio,
        "cobertura_territorial": cobertura_territorial,
        "concentracion_muestra_pct": round(concentracion_muestra, 1) if not pd.isna(concentracion_muestra) else np.nan,
        "comunidad_mayor_muestra": comunidad_mayor_n,
        "mejor_comunidad": mejor_comunidad,
        "peor_comunidad": peor_comunidad,
        "estado_semaforo": semaforo_estado(positividad_ultimo),
        "color_semaforo": semaforo_color(positividad_ultimo),
    }


def metricas_calidad(df: pd.DataFrame) -> Dict[str, float]:
    cols = ["año", "percepcion_final", "comunidad", "género", "nse", "estudios"]
    comp = {col: round(df[col].notna().mean() * 100, 1) for col in cols}
    comp["integridad_promedio_%"] = round(np.mean(list(comp.values())), 1)
    comp["registros"] = int(len(df))
    comp["años_cubiertos"] = int(df["año"].dropna().nunique()) if df["año"].notna().any() else 0
    comp["comunidades"] = int(df["comunidad"].dropna().nunique()) if df["comunidad"].notna().any() else 0
    return comp


def construir_resumen_ejecutivo(df: pd.DataFrame) -> Dict[str, Any]:
    anuales = construir_tabla_anual(df)
    comunidades = construir_tabla_comunidades(df, CFG.min_muestra_comunidad)
    dist_genero = construir_distribucion(df, "género")
    dist_nse = construir_distribucion(df, "nse")
    dist_estudios = construir_distribucion(df, "estudios")
    calidad_año = matriz_calidad_por_año(df, ["percepcion_final", "comunidad", "género", "nse", "estudios"])
    indices = calcular_indices_avanzados(df, anuales, comunidades)

    return {
        "anuales": anuales,
        "comunidades": comunidades,
        "dist_genero": dist_genero,
        "dist_nse": dist_nse,
        "dist_estudios": dist_estudios,
        "calidad_año": calidad_año,
        **indices
    }


# =========================================================
# 6. GRAFICOS MEJORADOS Y CREATIVOS
# =========================================================

def guardar_fig(fig, path: str) -> None:
    fig.tight_layout()
    fig.savefig(path, dpi=320, bbox_inches="tight")
    plt.close(fig)


def chart_tendencia_area(anuales: pd.DataFrame, path: str) -> None:
    fig, ax = plt.subplots(figsize=(10.8, 4.8))

    x = anuales["año"].astype(int).values
    y = anuales["Positiva_%"].values.astype(float)

    ax.fill_between(x, y, color=PALETTE["green_200"], alpha=0.85)
    ax.plot(x, y, color=PALETTE["green_800"], linewidth=3, marker="o", markersize=7)
    ax.scatter(x, y, s=80, color=PALETTE["green_700"], edgecolor=PALETTE["white"], linewidth=1.5, zorder=3)

    ax.axhline(50, color=PALETTE["gray_500"], linestyle="--", linewidth=1)
    ax.set_title("Evolucion anual de la percepcion positiva")
    ax.set_xlabel("Año")
    ax.set_ylabel("Positividad (%)")
    ax.yaxis.set_major_formatter(PercentFormatter())
    ax.set_ylim(0, max(60, math.ceil(np.nanmax(y) / 10) * 10 + 10))
    ax.grid(axis="y")

    for xi, yi in zip(x, y):
        ax.annotate(f"{yi:.1f}%", (xi, yi), textcoords="offset points", xytext=(0, 9), ha="center",
                    fontsize=9, fontweight="bold", color=PALETTE["green_900"])

    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)

    guardar_fig(fig, path)


def chart_stacked_100(anuales: pd.DataFrame, path: str) -> None:
    fig, ax = plt.subplots(figsize=(10.8, 5.0))
    x = np.arange(len(anuales))

    ax.bar(x, anuales["Positiva_%"], color=PALETTE["green_700"], label="Positiva")
    ax.bar(x, anuales["Neutra_%"], bottom=anuales["Positiva_%"], color=PALETTE["green_300"], label="Neutra")
    ax.bar(x, anuales["Negativa_%"], bottom=anuales["Positiva_%"] + anuales["Neutra_%"],
           color=PALETTE["gray_300"], label="Negativa")

    ax.set_xticks(x)
    ax.set_xticklabels(anuales["año"].astype(int).astype(str))
    ax.set_ylim(0, 100)
    ax.set_ylabel("Distribucion porcentual")
    ax.yaxis.set_major_formatter(PercentFormatter())
    ax.set_title("Composicion anual de la percepcion")
    ax.legend(frameon=False, ncol=3, loc="upper center", bbox_to_anchor=(0.5, 1.12))
    ax.grid(axis="y")

    for i, row in anuales.iterrows():
        ax.text(i, row["Positiva_%"] / 2, f"{row['Positiva_%']:.0f}%", ha="center", va="center",
                fontsize=9, color="white", fontweight="bold")

    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)

    guardar_fig(fig, path)


def chart_lollipop_comunidades(comunidades: pd.DataFrame, path: str, top_n: int) -> None:
    plot_df = comunidades.head(top_n).sort_values("positiva_%").copy()

    fig, ax = plt.subplots(figsize=(10.8, 6.2))
    y_pos = np.arange(len(plot_df))

    for i, (_, row) in enumerate(plot_df.iterrows()):
        color = PALETTE["green_700"] if row["positiva_%"] >= 70 else PALETTE["green_500"] if row["positiva_%"] >= 50 else PALETTE["gray_500"]
        ax.hlines(y=i, xmin=0, xmax=row["positiva_%"], color=PALETTE["green_200"], linewidth=3)
        ax.scatter(row["positiva_%"], i, s=110, color=color, edgecolor="white", linewidth=1.5, zorder=3)
        ax.text(row["positiva_%"] + 1.5, i, f"{row['positiva_%']:.1f}%  (n={int(row['n'])})",
                va="center", fontsize=8.8, color=PALETTE["gray_900"])

    ax.set_yticks(y_pos)
    ax.set_yticklabels(plot_df["comunidad"].map(lambda x: truncate(x, 28)))
    ax.set_xlim(0, 100)
    ax.xaxis.set_major_formatter(PercentFormatter())
    ax.set_xlabel("Positividad (%)")
    ax.set_title(f"Ranking territorial de positividad, ultimo año, n >= {CFG.min_muestra_comunidad}")
    ax.grid(axis="x")

    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)

    guardar_fig(fig, path)


def chart_scatter_territorial(comunidades: pd.DataFrame, path: str) -> None:
    if comunidades.empty:
        return

    plot_df = comunidades.copy()

    fig, ax = plt.subplots(figsize=(10.8, 6.0))
    sizes = np.clip(plot_df["n"].astype(float) * 18, 80, 900)
    colors = plot_df["positiva_%"].apply(semaforo_color).tolist()

    ax.scatter(
        plot_df["n"],
        plot_df["positiva_%"],
        s=sizes,
        c=colors,
        alpha=0.8,
        edgecolor="white",
        linewidth=1.2
    )

    ax.axhline(50, color=PALETTE["gray_500"], linestyle="--", linewidth=1)
    ax.set_xlabel("Tamaño muestral por comunidad")
    ax.set_ylabel("Positividad (%)")
    ax.set_title("Mapa de dispersion territorial, muestra vs positividad")
    ax.yaxis.set_major_formatter(PercentFormatter())
    ax.grid(True)

    top_label = plot_df.sort_values(["n", "positiva_%"], ascending=[False, False]).head(6)
    for _, row in top_label.iterrows():
        ax.annotate(
            truncate(row["comunidad"], 22),
            (row["n"], row["positiva_%"]),
            textcoords="offset points",
            xytext=(5, 5),
            fontsize=8.3,
            color=PALETTE["gray_900"]
        )

    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)

    guardar_fig(fig, path)


def donut(ax, values, labels, colors, title):
    total = np.sum(values)
    if total <= 0:
        ax.axis("off")
        return

    ax.pie(
        values,
        labels=None,
        colors=colors,
        startangle=90,
        wedgeprops={"width": 0.38, "edgecolor": "white"}
    )
    ax.add_artist(Circle((0, 0), 0.42, color="white"))
    ax.text(0, 0.03, f"{int(total)}", ha="center", va="center", fontsize=16, fontweight="bold", color=PALETTE["green_800"])
    ax.text(0, -0.16, "casos", ha="center", va="center", fontsize=9, color=PALETTE["gray_700"])
    ax.set_title(title, fontsize=12, fontweight="bold", color=PALETTE["green_900"])

    legend_labels = [f"{truncate(l, 22)} ({v:.1f}%)" for l, v in zip(labels, values)]
    ax.legend(legend_labels, loc="lower center", bbox_to_anchor=(0.5, -0.26), frameon=False, fontsize=8, ncol=1)


def chart_donuts_perfil(dist_genero: pd.DataFrame, dist_nse: pd.DataFrame, path: str) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(10.8, 5.0))

    if not dist_genero.empty:
        donut(
            axes[0],
            dist_genero["%"].values,
            dist_genero["género"].values,
            [PALETTE["green_800"], PALETTE["green_400"], PALETTE["gray_300"]][:len(dist_genero)],
            "Perfil por genero"
        )
    else:
        axes[0].axis("off")

    if not dist_nse.empty:
        donut(
            axes[1],
            dist_nse["%"].values,
            dist_nse["nse"].values,
            [PALETTE["green_900"], PALETTE["green_600"], PALETTE["green_300"], PALETTE["gray_300"]][:len(dist_nse)],
            "Perfil por NSE"
        )
    else:
        axes[1].axis("off")

    guardar_fig(fig, path)


def chart_estudios_horizontal(dist_estudios: pd.DataFrame, path: str) -> None:
    plot_df = dist_estudios.sort_values("%").copy()

    fig, ax = plt.subplots(figsize=(9.2, 4.8))
    bars = ax.barh(
        plot_df["estudios"].map(lambda x: truncate(x, 30)),
        plot_df["%"],
        color=[PALETTE["green_300"], PALETTE["green_400"], PALETTE["green_500"], PALETTE["green_700"], PALETTE["green_800"]][:len(plot_df)]
    )

    ax.set_title("Distribucion del panel por nivel educativo")
    ax.set_xlabel("Participacion (%)")
    ax.xaxis.set_major_formatter(PercentFormatter())
    ax.grid(axis="x")

    for bar, v in zip(bars, plot_df["%"]):
        ax.text(v + 1.0, bar.get_y() + bar.get_height() / 2, f"{v:.1f}%", va="center", fontsize=9)

    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)

    guardar_fig(fig, path)


def chart_heatmap_calidad(calidad_año: pd.DataFrame, path: str) -> None:
    if calidad_año.empty:
        return

    plot_df = calidad_año.copy()
    data = plot_df.values

    fig, ax = plt.subplots(figsize=(10.8, 4.8))
    im = ax.imshow(data, aspect="auto", cmap="Greens", vmin=0, vmax=100)

    ax.set_xticks(np.arange(plot_df.shape[1]))
    ax.set_xticklabels([truncate(c, 18) for c in plot_df.columns], rotation=20, ha="right")
    ax.set_yticks(np.arange(plot_df.shape[0]))
    ax.set_yticklabels(plot_df.index.astype(int).astype(str))
    ax.set_title("Heatmap de completitud por año y variable")

    for i in range(plot_df.shape[0]):
        for j in range(plot_df.shape[1]):
            val = data[i, j]
            txt_color = "white" if val >= 65 else PALETTE["gray_900"]
            ax.text(j, i, f"{val:.0f}", ha="center", va="center", fontsize=8.6, color=txt_color, fontweight="bold")

    cbar = fig.colorbar(im, ax=ax, fraction=0.035, pad=0.03)
    cbar.set_label("Completitud (%)")

    guardar_fig(fig, path)


def chart_semicirculo_semaforo(valor: float, path: str) -> None:
    fig, ax = plt.subplots(figsize=(7.8, 4.6))
    ax.set_aspect("equal")
    ax.axis("off")

    wedges = [
        (180, 120, PALETTE["red_soft"]),
        (120, 60, PALETTE["amber_soft"]),
        (60, 0, PALETTE["green_700"]),
    ]
    for start, end, color in wedges:
        ax.add_patch(Wedge((0, 0), 1.0, end, start, width=0.28, facecolor=color, edgecolor="white"))

    angle = 180 - (max(0, min(100, valor)) / 100) * 180
    x = 0.78 * math.cos(math.radians(angle))
    y = 0.78 * math.sin(math.radians(angle))
    ax.plot([0, x], [0, y], color=PALETTE["green_900"], linewidth=3)
    ax.add_patch(Circle((0, 0), 0.04, color=PALETTE["green_900"]))

    ax.text(0, -0.05, f"{valor:.1f}%", ha="center", va="center", fontsize=20, fontweight="bold", color=PALETTE["green_900"])
    ax.text(0, -0.22, "positividad", ha="center", va="center", fontsize=10, color=PALETTE["gray_700"])

    ax.text(-0.95, -0.02, "Critico", ha="left", va="center", fontsize=9, color=PALETTE["red_soft"])
    ax.text(0, 1.04, "Atencion", ha="center", va="center", fontsize=9, color=PALETTE["amber_soft"])
    ax.text(0.95, -0.02, "Favorable", ha="right", va="center", fontsize=9, color=PALETTE["green_700"])

    ax.set_xlim(-1.15, 1.15)
    ax.set_ylim(-0.35, 1.15)

    guardar_fig(fig, path)


def chart_top_muestra(comunidades: pd.DataFrame, path: str, top_n: int) -> None:
    if comunidades.empty:
        return

    plot_df = comunidades.sort_values("n", ascending=True).tail(top_n)

    fig, ax = plt.subplots(figsize=(10.8, 5.8))
    bars = ax.barh(
        plot_df["comunidad"].map(lambda x: truncate(x, 28)),
        plot_df["n"],
        color=PALETTE["green_500"]
    )

    ax.set_title("Comunidades con mayor tamaño muestral, ultimo año")
    ax.set_xlabel("Numero de casos")
    ax.grid(axis="x")

    for bar, n in zip(bars, plot_df["n"]):
        ax.text(bar.get_width() + 0.8, bar.get_y() + bar.get_height() / 2, f"{int(n)}", va="center", fontsize=8.8)

    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)

    guardar_fig(fig, path)


def crear_graficos(df: pd.DataFrame, resumen: Dict[str, Any], out_dir: str) -> Dict[str, str]:
    configurar_estilo_graficos()
    ensure_dir(out_dir)

    archivos = {}

    anuales = resumen["anuales"]
    comunidades = resumen["comunidades"]
    dist_genero = resumen["dist_genero"]
    dist_nse = resumen["dist_nse"]
    dist_estudios = resumen["dist_estudios"]
    calidad_año = resumen["calidad_año"]

    if not anuales.empty:
        p = os.path.join(out_dir, "tendencia_area.png")
        chart_tendencia_area(anuales, p)
        archivos["tendencia_area"] = p

        p = os.path.join(out_dir, "composicion_100.png")
        chart_stacked_100(anuales, p)
        archivos["composicion_100"] = p

        p = os.path.join(out_dir, "semaforo.png")
        chart_semicirculo_semaforo(resumen["positividad_ultimo"], p)
        archivos["semaforo"] = p

    if not comunidades.empty:
        p = os.path.join(out_dir, "lollipop_comunidades.png")
        chart_lollipop_comunidades(comunidades, p, CFG.top_n_comunidades)
        archivos["lollipop_comunidades"] = p

        p = os.path.join(out_dir, "scatter_territorial.png")
        chart_scatter_territorial(comunidades, p)
        archivos["scatter_territorial"] = p

        p = os.path.join(out_dir, "top_muestra.png")
        chart_top_muestra(comunidades, p, CFG.top_n_muestra)
        archivos["top_muestra"] = p

    if not dist_genero.empty or not dist_nse.empty:
        p = os.path.join(out_dir, "donuts_perfil.png")
        chart_donuts_perfil(dist_genero, dist_nse, p)
        archivos["donuts_perfil"] = p

    if not dist_estudios.empty:
        p = os.path.join(out_dir, "estudios_horizontal.png")
        chart_estudios_horizontal(dist_estudios, p)
        archivos["estudios_horizontal"] = p

    if not calidad_año.empty:
        p = os.path.join(out_dir, "heatmap_calidad.png")
        chart_heatmap_calidad(calidad_año, p)
        archivos["heatmap_calidad"] = p

    return archivos


# =========================================================
# 7. REPORTE PDF ULTRA MEJORADO
# =========================================================

class ReporteIntegralPDF(FPDF):
    def __init__(self, logo_path: Optional[str] = None):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.logo_path = logo_path
        self.set_auto_page_break(auto=True, margin=16)
        self.alias_nb_pages()

    def t(self, txt: Any) -> str:
        return ascii_text(txt)

    def header(self):
        if self.page_no() == 1:
            return
        self.set_y(8)
        self.set_font("Arial", "B", 9)
        self.set_text_color(90, 90, 90)
        self.cell(0, 5, self.t("PARACEL | Reporte integral de percepcion e impacto social"), 0, 0, "R")
        self.ln(7)
        self.set_draw_color(220, 220, 220)
        self.line(10, 16, 200, 16)
        self.ln(3)

    def footer(self):
        if self.page_no() == 1:
            return
        self.set_y(-12)
        self.set_draw_color(220, 220, 220)
        self.line(10, self.get_y() - 2, 200, self.get_y() - 2)
        self.set_font("Arial", "I", 8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 6, f"Pagina {self.page_no()} de {{nb}}", 0, 0, "C")

    def portada(self, titulo: str, subtitulo: str, periodo: str, universo: int):
        self.add_page()
        self.set_fill_color(11, 61, 46)
        self.rect(0, 0, 210, 297, style="F")

        self.set_fill_color(255, 255, 255)
        self.rect(10, 12, 190, 273, style="F")

        self.set_fill_color(216, 240, 210)
        self.rect(10, 12, 190, 16, style="F")

        if self.logo_path and os.path.exists(self.logo_path):
            self.image(self.logo_path, x=68, y=34, w=74)

        self.set_xy(16, 108)
        self.set_font("Arial", "B", 24)
        self.set_text_color(11, 61, 46)
        self.multi_cell(178, 11, self.t(titulo), 0, "C")

        self.ln(3)
        self.set_font("Arial", "", 14)
        self.set_text_color(95, 95, 95)
        self.multi_cell(178, 8, self.t(subtitulo), 0, "C")

        self.ln(12)
        self.set_font("Arial", "B", 12)
        self.set_text_color(70, 70, 70)
        self.cell(178, 8, self.t(f"Periodo analizado: {periodo}"), 0, 1, "C")

        self.set_font("Arial", "", 11)
        self.cell(178, 8, self.t(f"Registros procesados y validados: {format_num(universo, decimals=0)}"), 0, 1, "C")

        self.set_y(245)
        self.set_fill_color(238, 248, 236)
        self.set_draw_color(220, 235, 220)
        self.rect(22, 240, 166, 24, style="FD")
        self.set_xy(28, 246)
        self.set_font("Arial", "", 10)
        self.set_text_color(85, 85, 85)
        self.multi_cell(
            154,
            5.5,
            self.t(
                "Documento generado automaticamente a partir de la base consolidada. "
                "Incluye control de calidad, metricas ejecutivas, tablas analiticas y visualizaciones avanzadas."
            ),
            0,
            "C"
        )

    def section_title(self, text: str):
        self.ln(1)
        self.set_fill_color(11, 81, 50)
        self.set_text_color(255, 255, 255)
        self.set_font("Arial", "B", 13)
        self.cell(0, 9, self.t(text), 0, 1, "L", 1)
        self.ln(3)

    def subsection_title(self, text: str):
        self.set_font("Arial", "B", 11.3)
        self.set_text_color(20, 90, 55)
        self.cell(0, 7, self.t(text), 0, 1, "L")
        self.ln(1)

    def paragraph(self, text: str, size: float = 10.5):
        self.set_font("Arial", "", size)
        self.set_text_color(45, 45, 45)
        self.multi_cell(0, 6, self.t(text))
        self.ln(1.5)

    def note_box(self, text: str):
        x = 10
        y = self.get_y()
        h = 18 + (max(0, len(self.t(text)) - 100) // 75) * 5
        self.set_fill_color(238, 248, 236)
        self.set_draw_color(204, 227, 207)
        self.rect(x, y, 190, h, style="FD")
        self.set_xy(x + 4, y + 3)
        self.set_font("Arial", "", 10)
        self.set_text_color(55, 55, 55)
        self.multi_cell(182, 5.5, self.t(text))
        self.ln(2)

    def kpi_row(self, cards: List[Tuple[str, str, Tuple[int, int, int]]]):
        x0 = 10
        y0 = self.get_y()
        gap = 4
        card_w = (190 - gap * (len(cards) - 1)) / len(cards)
        card_h = 26

        for i, (value, label, rgb) in enumerate(cards):
            x = x0 + i * (card_w + gap)
            self.set_xy(x, y0)
            self.set_fill_color(247, 247, 247)
            self.set_draw_color(225, 225, 225)
            self.rect(x, y0, card_w, card_h, style="FD")

            self.set_fill_color(*rgb)
            self.rect(x, y0, card_w, 4.2, style="F")

            self.set_xy(x + 2, y0 + 6)
            self.set_font("Arial", "B", 15)
            self.set_text_color(*rgb)
            self.cell(card_w - 4, 6, self.t(value), 0, 2, "C")

            self.set_font("Arial", "", 8.7)
            self.set_text_color(95, 95, 95)
            self.multi_cell(card_w - 4, 4.2, self.t(label), 0, "C")

        self.set_y(y0 + card_h + 4)

    def metric_box(self, title: str, value: str, x: float, y: float, w: float = 58, h: float = 20):
        self.set_xy(x, y)
        self.set_fill_color(238, 248, 236)
        self.set_draw_color(208, 230, 210)
        self.rect(x, y, w, h, style="FD")

        self.set_xy(x + 2, y + 3)
        self.set_font("Arial", "", 8.5)
        self.set_text_color(100, 100, 100)
        self.multi_cell(w - 4, 4, self.t(title), 0, "C")

        self.set_xy(x + 2, y + 11)
        self.set_font("Arial", "B", 12)
        self.set_text_color(11, 81, 50)
        self.cell(w - 4, 5, self.t(value), 0, 0, "C")

    def insert_image(self, path: str, x: float = 12, w: float = 186, h_mm: float = 0):
        if path and os.path.exists(path):
            if h_mm > 0 and self.get_y() + h_mm > 270:
                self.add_page()
            self.image(path, x=x, y=self.get_y(), w=w)
            if h_mm > 0:
                self.ln(h_mm + 4)
            else:
                self.ln(4)

    def simple_table(self, df: pd.DataFrame, widths: List[float], headers: List[str], align: Optional[List[str]] = None):
        if df.empty:
            self.paragraph("No se dispone de informacion suficiente para esta tabla.")
            return

        align = align or ["L"] * len(headers)

        self.set_fill_color(15, 81, 50)
        self.set_text_color(255, 255, 255)
        self.set_font("Arial", "B", 9)

        for head, w in zip(headers, widths):
            self.cell(w, 7, self.t(head), 1, 0, "C", 1)
        self.ln()

        self.set_font("Arial", "", 8.6)
        self.set_text_color(45, 45, 45)

        alt = False
        for _, row in df.iterrows():
            fill = (247, 250, 247) if alt else (239, 246, 239)
            alt = not alt
            self.set_fill_color(*fill)

            for j, (col, w) in enumerate(zip(df.columns, widths)):
                val = row[col]
                if isinstance(val, (float, np.floating)):
                    txt = format_num(val, decimals=1)
                else:
                    txt = ascii_text(val)
                txt = truncate(txt, max(8, int(w * 1.8)))
                self.cell(w, 6.5, self.t(txt), 1, 0, align[j], 1)
            self.ln()

            if self.get_y() > 265:
                self.add_page()
                self.set_fill_color(15, 81, 50)
                self.set_text_color(255, 255, 255)
                self.set_font("Arial", "B", 9)
                for head, w in zip(headers, widths):
                    self.cell(w, 7, self.t(head), 1, 0, "C", 1)
                self.ln()
                self.set_font("Arial", "", 8.6)
                self.set_text_color(45, 45, 45)

        self.ln(3)

    def toc_item(self, idx: str, text: str):
        self.set_font("Arial", "", 10.5)
        self.set_text_color(55, 55, 55)
        self.cell(16, 6.2, self.t(idx), 0, 0, "L")
        self.cell(0, 6.2, self.t(text), 0, 1, "L")

    def responsables(self, path_img_1: str, path_img_2: str):
        self.add_page()
        self.section_title("7. Direccion y Responsables del Monitoreo")
        self.paragraph("El presente informe ha sido elaborado, revisado y validado por el equipo de Monitoreo de Impactos y la Direccion de Comunicacion y Sustentabilidad Social de PARACEL.")
        
        if path_img_1 and os.path.exists(path_img_1):
            self.image(path_img_1, x=15, y=self.get_y()+8, w=180)
            self.ln(45)
            
        if path_img_2 and os.path.exists(path_img_2):
            self.image(path_img_2, x=15, y=self.get_y()+8, w=180)
            self.ln(45)

# =========================================================
# 8. TEXTO DINAMICO DEL INFORME
# =========================================================

def texto_resumen_ejecutivo(resumen: Dict[str, Any]) -> str:
    ultimo = resumen["ultimo_año"]
    pos = resumen["positividad_ultimo"]
    bal = resumen["balance_ultimo"]
    delta = resumen["delta_vs_prev"]
    muestra = resumen["muestra_ultimo"]
    integridad = resumen["calidad"]["integridad_promedio_%"]
    volatilidad = resumen["volatilidad_positividad"]

    partes = [
        f"El ultimo corte disponible corresponde al año {ultimo}, con una muestra valida de {format_num(muestra, decimals=0)} registros.",
        f"La percepcion positiva alcanzo {format_num(pos, pct=True)} y el balance neto entre positividad y negatividad fue de {format_num(bal)} puntos porcentuales.",
        f"El promedio de completitud de las variables estructurales analizadas fue de {format_num(integridad, pct=True)}.",
        f"La volatilidad historica de la positividad, medida como la desviacion estandar interanual, fue de {format_num(volatilidad)} puntos porcentuales."
    ]

    if pd.notna(delta):
        sentido = "aumento" if delta >= 0 else "disminuyo"
        if delta >= 0:
            partes.append(f"Respecto al año previo, la positividad aumento en {format_num(abs(delta))} puntos porcentuales.")
        else:
            partes.append(f"Respecto al año previo, la positividad disminuyo en {format_num(abs(delta))} puntos porcentuales.")

    if resumen["mejor_comunidad"] is not None and resumen["peor_comunidad"] is not None:
        mc = resumen["mejor_comunidad"]
        pc = resumen["peor_comunidad"]
        partes.append(
            f"En el ultimo año, la comunidad con mejor resultado observado fue {mc['comunidad']} "
            f"({format_num(mc['positiva_%'], pct=True)}; n={format_num(mc['n'], decimals=0)}), mientras que la menor positividad se observo en "
            f"{pc['comunidad']} ({format_num(pc['positiva_%'], pct=True)}; n={format_num(pc['n'], decimals=0)})."
        )

    return " ".join(partes)


def texto_metodologia(df: pd.DataFrame, resumen: Dict[str, Any]) -> str:
    anios = sorted([int(x) for x in df["año"].dropna().unique().tolist()]) if df["año"].notna().any() else []
    periodo = f"{min(anios)} a {max(anios)}" if anios else "sin periodo definido"
    comunidades = resumen["calidad"]["comunidades"]
    return (
        f"El reporte se construye a partir de una base consolidada de serie historica, depurada y homologada para el periodo {periodo}. "
        f"Se ejecutaron procesos de estandarizacion de nombres de variables, normalizacion de categorias de percepcion, genero, nivel socioeconomico y estudios, "
        f"asi como controles de valores faltantes en campos criticos. El universo analitico comprende {format_num(len(df), decimals=0)} registros y "
        f"{format_num(comunidades, decimals=0)} comunidades o unidades territoriales identificadas."
    )


def texto_calidad(resumen: Dict[str, Any]) -> str:
    cal = resumen["calidad"]
    return (
        f"La calidad estructural de la base fue evaluada mediante tasas de completitud por variable. "
        f"Los niveles observados fueron: año {format_num(cal['año'], pct=True)}, percepcion final {format_num(cal['percepcion_final'], pct=True)}, "
        f"comunidad {format_num(cal['comunidad'], pct=True)}, genero {format_num(cal['género'], pct=True)}, "
        f"nivel socioeconomico {format_num(cal['nse'], pct=True)} y estudios {format_num(cal['estudios'], pct=True)}. "
        f"El promedio global de integridad se ubico en {format_num(cal['integridad_promedio_%'], pct=True)}."
    )


def texto_hallazgos_territoriales(resumen: Dict[str, Any]) -> str:
    cobertura = resumen["cobertura_territorial"]
    conc = resumen["concentracion_muestra_pct"]
    mayor = resumen["comunidad_mayor_muestra"]

    txt = (
        f"En el ultimo año, la lectura territorial disponible cubre {format_num(cobertura, decimals=0)} comunidades con identificacion valida. "
        f"La concentracion de la muestra en la comunidad con mayor numero de observaciones alcanza {format_num(conc, pct=True)}"
    )
    if mayor:
        txt += f", correspondiente a {mayor}"
    txt += ". "
    txt += (
        "Por ello, la interpretacion territorial debe combinar simultaneamente el porcentaje de positividad y el tamaño muestral, "
        "evitando conclusiones excesivas sobre comunidades con pocos casos."
    )
    return txt


def recomendaciones_tecnicas(resumen: Dict[str, Any]) -> List[str]:
    recs = [
        "Establecer un diccionario unico de categorias para percepcion, genero, NSE, comunidad y estudios, para evitar recodificaciones posteriores.",
        "Incorporar un identificador anonimo persistente por informante, permitiendo analizar la serie como panel longitudinal real.",
        "Registrar una fecha exacta de levantamiento, adicional al año, para estudiar estacionalidad, coyunturas y efectos de hitos corporativos.",
        "Definir reglas de publicacion territorial con umbrales minimos de muestra y etiquetas de precision, a fin de reducir inferencias inestables.",
        "Construir un tablero interactivo complementario que permita filtrar por año, comunidad, perfil y tipo de percepcion, con recalculo inmediato de KPI."
    ]
    if resumen["calidad"]["integridad_promedio_%"] < 85:
        recs.insert(
            0,
            "Priorizar un plan de fortalecimiento de la calidad del dato, especialmente en variables de perfil y localizacion, antes de profundizar cortes finos por segmentos."
        )
    if not pd.isna(resumen["concentracion_muestra_pct"]) and resumen["concentracion_muestra_pct"] >= 25:
        recs.insert(
            1,
            "Revisar el diseño de campo para reducir la concentracion muestral en pocas comunidades y mejorar la representatividad territorial comparativa."
        )
    return recs


def dataframe_anual_reporte(anuales: pd.DataFrame) -> pd.DataFrame:
    if anuales.empty:
        return anuales
    out = anuales[["año", "Total", "Positiva_%", "Neutra_%", "Negativa_%", "Balance_neto_pp", "Var_Pos_pp_vs_prev"]].copy()
    out.columns = ["Año", "n", "Positiva %", "Neutra %", "Negativa %", "Balance neto", "Var. vs previo"]
    out["n"] = out["n"].astype(int)
    return out


def dataframe_comunidades_reporte(comunidades: pd.DataFrame) -> pd.DataFrame:
    if comunidades.empty:
        return comunidades
    out = comunidades[["comunidad", "n", "positiva_%", "negativa_%", "balance_neto_pp"]].head(10).copy()
    out.columns = ["Comunidad", "n", "Positiva %", "Negativa %", "Balance neto"]
    out["n"] = out["n"].astype(int)
    return out


def dataframe_calidad_reporte(cal: Dict[str, Any]) -> pd.DataFrame:
    return pd.DataFrame({
        "Variable": ["Año", "Percepcion final", "Comunidad", "Genero", "NSE", "Estudios", "Promedio"],
        "Completitud %": [
            cal["año"], cal["percepcion_final"], cal["comunidad"],
            cal["género"], cal["nse"], cal["estudios"], cal["integridad_promedio_%"]
        ]
    })


# =========================================================
# 9. ENSAMBLAJE DEL PDF
# =========================================================

def ensamblar_pdf(df: pd.DataFrame, resumen: Dict[str, Any], graficos: Dict[str, str], cfg: Config) -> None:
    pdf = ReporteIntegralPDF(logo_path=cfg.logo_path)

    años = sorted(df["año"].dropna().astype(int).unique().tolist()) if df["año"].notna().any() else []
    periodo = f"{min(años)} - {max(años)}" if años else "Sin periodo"

    pdf.portada(
        titulo="Reporte integral ejecutivo",
        subtitulo="Monitoreo longitudinal de percepcion e impacto social",
        periodo=periodo,
        universo=len(df)
    )

    pdf.add_page()
    pdf.section_title("Indice del documento")
    pdf.toc_item("1.", "Resumen ejecutivo y tablero de indicadores")
    pdf.toc_item("2.", "Base de datos, homologacion y control de calidad")
    pdf.toc_item("3.", "Evolucion temporal de la percepcion")
    pdf.toc_item("4.", "Analisis territorial del ultimo año")
    pdf.toc_item("5.", "Perfil sociodemografico del panel")
    pdf.toc_item("6.", "Conclusiones y recomendaciones tecnicas")
    pdf.toc_item("7.", "Direccion y Responsables del Monitoreo")
    pdf.ln(4)

    pdf.note_box(
        "El informe combina lectura ejecutiva, metricas de seguimiento, evidencia grafica y tablas analiticas, "
        "con enfasis en consistencia visual, interpretacion territorial y trazabilidad de la calidad del dato."
    )

    pdf.add_page()
    pdf.section_title("1. Resumen ejecutivo y tablero de indicadores")
    pdf.paragraph(texto_resumen_ejecutivo(resumen))

    delta_txt = "N/D" if pd.isna(resumen["delta_vs_prev"]) else f"{resumen['delta_vs_prev']:+.1f} pp"
    pdf.kpi_row([
        (f"{resumen['positividad_ultimo']:.1f}%", "Positividad en el ultimo año", (20, 108, 67)),
        (f"{resumen['balance_ultimo']:.1f} pp", "Balance neto de percepcion", (11, 61, 46)),
        (delta_txt, "Variacion frente al año previo", (46, 139, 87)),
        (f"{resumen['calidad']['integridad_promedio_%']:.1f}%", "Integridad promedio de la base", (124, 188, 130)),
    ])

    y = pdf.get_y()
    pdf.metric_box("Estado semaforo", resumen["estado_semaforo"], 10, y, w=58)
    pdf.metric_box("Cobertura territorial", format_num(resumen["cobertura_territorial"], decimals=0), 76, y, w=58)
    pdf.metric_box("Volatilidad historica", f"{resumen['volatilidad_positividad']:.1f} pp", 142, y, w=58)
    pdf.set_y(y + 25)

    if "semaforo" in graficos:
        pdf.insert_image(graficos["semaforo"], x=48, w=114, h_mm=58)

    pdf.note_box(
        "La lectura ejecutiva debe considerar simultaneamente tres dimensiones: nivel de positividad, evolucion interanual y estabilidad territorial de los resultados."
    )

    pdf.add_page()
    pdf.section_title("2. Base de datos, homologacion y control de calidad")
    pdf.subsection_title("2.1 Estructura analitica del insumo")
    pdf.paragraph(texto_metodologia(df, resumen))

    pdf.subsection_title("2.2 Evaluacion de calidad del dato")
    pdf.paragraph(texto_calidad(resumen))

    tabla_calidad = dataframe_calidad_reporte(resumen["calidad"])
    pdf.simple_table(
        tabla_calidad,
        widths=[110, 40],
        headers=["Variable", "Completitud %"],
        align=["L", "C"]
    )

    if "heatmap_calidad" in graficos:
        pdf.subsection_title("2.3 Heatmap de completitud por año")
        pdf.insert_image(graficos["heatmap_calidad"], x=12, w=186, h_mm=82)

    pdf.add_page()
    pdf.section_title("3. Evolucion temporal de la percepcion")
    pdf.subsection_title("3.1 Tendencia anual de la positividad")
    pdf.paragraph("La serie anual sintetiza la trayectoria de aceptacion social del proyecto.")
    if "tendencia_area" in graficos:
        pdf.insert_image(graficos["tendencia_area"], x=12, w=186, h_mm=80)

    pdf.subsection_title("3.2 Composicion anual de respuestas")
    pdf.paragraph("Adicionalmente al indicador de positividad, se examina la estructura completa de respuestas.")
    if "composicion_100" in graficos:
        pdf.insert_image(graficos["composicion_100"], x=12, w=186, h_mm=84)

    tabla_anual = dataframe_anual_reporte(resumen["anuales"])
    pdf.simple_table(
        tabla_anual,
        widths=[18, 18, 25, 25, 25, 34, 35],
        headers=["Año", "n", "Positiva %", "Neutra %", "Negativa %", "Balance neto", "Var. vs previo"],
        align=["C", "C", "C", "C", "C", "C", "C"]
    )

    pdf.add_page()
    pdf.section_title("4. Analisis territorial del ultimo año")
    pdf.paragraph(texto_hallazgos_territoriales(resumen))

    pdf.subsection_title("4.1 Ranking territorial de positividad")
    if "lollipop_comunidades" in graficos:
        pdf.insert_image(graficos["lollipop_comunidades"], x=12, w=186, h_mm=98)

    pdf.subsection_title("4.2 Mapa de dispersion territorial")
    if "scatter_territorial" in graficos:
        pdf.insert_image(graficos["scatter_territorial"], x=12, w=186, h_mm=92)

    tabla_com = dataframe_comunidades_reporte(resumen["comunidades"])
    pdf.simple_table(
        tabla_com,
        widths=[86, 18, 26, 26, 34],
        headers=["Comunidad", "n", "Positiva %", "Negativa %", "Balance neto"],
        align=["L", "C", "C", "C", "C"]
    )

    pdf.subsection_title("4.3 Comunidades con mayor tamaño muestral")
    if "top_muestra" in graficos:
        pdf.insert_image(graficos["top_muestra"], x=12, w=186, h_mm=88)

    pdf.add_page()
    pdf.section_title("5. Perfil sociodemografico del panel")
    pdf.paragraph("La composicion sociodemografica del panel condiciona la interpretacion del resultado agregado.")

    if "donuts_perfil" in graficos:
        pdf.subsection_title("5.1 Distribucion por genero y nivel socioeconomico")
        pdf.insert_image(graficos["donuts_perfil"], x=12, w=186, h_mm=88)

    if "estudios_horizontal" in graficos:
        pdf.subsection_title("5.2 Distribucion por nivel educativo")
        pdf.insert_image(graficos["estudios_horizontal"], x=20, w=170, h_mm=78)

    pdf.add_page()
    pdf.section_title("6. Conclusiones y recomendaciones tecnicas")
    pdf.paragraph("En conjunto, la base permite construir una lectura ejecutiva consistente sobre el clima de percepcion alrededor del proyecto.")

    for i, rec in enumerate(recomendaciones_tecnicas(resumen), start=1):
        pdf.paragraph(f"{i}. {rec}")

    pdf.responsables("firma_latifi.png", "firma_diego.png")

    pdf.output(cfg.output_path)


def generar_docx(pdf_path: str, docx_path: str) -> None:
    print(f"Comenzando conversión de PDF a DOCX: {docx_path}")
    try:
        cv = Converter(pdf_path)
        cv.convert(docx_path, start=0, end=None)
        cv.close()
        print("¡La version Word se ha generado exitosamente!")
    except Exception as e:
        print(f"Error al generar versión Word: {e}")

# =========================================================
# 10. FLUJO PRINCIPAL
# =========================================================

def main():
    temp_dir = tempfile.mkdtemp(prefix="reporte_percepcion_ultra_")
    try:
        df = cargar_y_preparar_datos(CFG.file_path)
        resumen = construir_resumen_ejecutivo(df)
        graficos = crear_graficos(df, resumen, temp_dir)
        ensamblar_pdf(df, resumen, graficos, CFG)
        
        docx_path = CFG.output_path.replace('.pdf', '.docx')
        generar_docx(CFG.output_path, docx_path)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    main()

