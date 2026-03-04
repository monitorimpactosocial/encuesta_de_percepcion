import geopandas as gpd
import json
import os
import glob

# Rutas
DIR_MAPAS = "mapas_base"
OUTPUT_FILE = "mapas_data.js"

print("Iniciando procesamiento de cartografia para la Web...")

# Asegurarse de usar un CRS estandar para web (WGS84 EPSG:4326)
def procesar_shape(file_path):
    print(f"-> Leyendo {os.path.basename(file_path)}...")
    try:
        gdf = gpd.read_file(file_path)
        if gdf.crs is None or gdf.crs.to_string() != 'EPSG:4326':
            print(f"   Convirtiendo CRS a EPSG:4326...")
            gdf = gdf.to_crs(epsg=4326)
        
        # Rellenar nulos
        gdf = gdf.fillna("")
        
        # Retornar diccionario feature collection
        return json.loads(gdf.to_json())
    except Exception as e:
        print(f"   ERROR: No se pudo procesar - {str(e)}")
        return None

# Nombres legibles para el frontend
nombres_capas = {
    'PARACEL_PropiedadesForestales.shp': 'propiedades_forestales',
    'ComponentesPARACEL.shp': 'componentes_industriales',
    'Comunidades_Indígenas_Paracel.shp': 'comunidades_indigenas',
    'Comunidades_Industrial_Paracel.shp': 'comunidades_industriales',
    'Comunidades_Forestal_Paracel.shp': 'comunidades_forestales',
    'ComunidadesParacel_Limites.shp': 'comunidades_limites',
    'BarLoc2022_Concepción.shp': 'barrios_concepcion',
    'BarLoc2022_Amambay.shp': 'barrios_amambay',
    'Distritos_Paracel3.shp': 'distritos_paracel'
}

mapas_coleccion = {}

# Procesar cada shape
archivos_shp = glob.glob(os.path.join(DIR_MAPAS, "*.shp"))

for archivo in archivos_shp:
    nombre_base = os.path.basename(archivo)
    if nombre_base in nombres_capas:
        clave_web = nombres_capas[nombre_base]
    else:
        clave_web = nombre_base.replace(".shp", "").lower()
        
    resultado = procesar_shape(archivo)
    if resultado:
        mapas_coleccion[clave_web] = resultado

print(f"Escribiendo a {OUTPUT_FILE}...")
with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
    f.write(f"const mapasData = {json.dumps(mapas_coleccion, ensure_ascii=False)};\n")

print("¡Proceso de conversion a GeoJSON interactivo finalizado con exito!")
