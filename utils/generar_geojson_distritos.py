from pathlib import Path
import sys
import pandas as pd
import geopandas as gpd


# ============================================================================
# PATHS
# ============================================================================

PROJECT_DIR = Path(__file__).resolve().parents[1]

SRC_DIR = PROJECT_DIR / "src"
UTILS_DIR = PROJECT_DIR / "utils"

for path in [SRC_DIR, UTILS_DIR, PROJECT_DIR]:
    if str(path) not in sys.path:
        sys.path.append(str(path))

from limpieza_ig import limpiar_ig, to_geopandas


IG_PATH = PROJECT_DIR / "data" / "ig_distrito.csv"
INDICE_PATH = PROJECT_DIR / "output" / "indice_af.csv"

WEB_DATA_DIR = PROJECT_DIR / "geoton-web" / "public" / "data"
WEB_DATA_DIR.mkdir(parents=True, exist_ok=True)

GEOJSON_OUT = WEB_DATA_DIR / "distritos_simplificado.geojson"
INDICE_JSON_OUT = WEB_DATA_DIR / "indice_af.json"


# ============================================================================
# CONFIG
# ============================================================================

RENAME_MAP = {
    "categoria": "clasificacion",
    "privaciones": "n_privaciones",
    "pct_nbi": "pct_nbi_real",
    "intervencion": "intervencion_recomendada",
}


SERVICIOS = {
    "priv_salud_1": "Hospital lejano",
    "priv_salud_2": "Población sin seguro",
    "priv_edu_1": "Secundaria lejana",
    "priv_edu_2": "Analfabetismo",
    "priv_digital_1": "Sin internet",
    "priv_digital_2": "Baja cobertura 4G",
    "priv_basic_1": "Sin agua",
    "priv_basic_2": "Sin saneamiento",
    "priv_econ_1": "Desempleo",
    "priv_econ_2": "Sin documento",
}


DIMENSIONES = {
    "Salud": ["priv_salud_1", "priv_salud_2"],
    "Educación": ["priv_edu_1", "priv_edu_2"],
    "Conectividad": ["priv_digital_1", "priv_digital_2"],
    "Servicios básicos": ["priv_basic_1", "priv_basic_2"],
    "Empleo / documentación": ["priv_econ_1", "priv_econ_2"],
}


# ============================================================================
# HELPERS
# ============================================================================

def validar_archivos():
    if not IG_PATH.exists():
        raise FileNotFoundError(
            f"No encontré ig_distrito.csv en:\n{IG_PATH}\n\n"
            f"Verifica que exista este archivo:\n"
            f"data/ig_distrito.csv"
        )

    if not INDICE_PATH.exists():
        raise FileNotFoundError(
            f"No encontré indice_af.csv en:\n{INDICE_PATH}\n\n"
            f"Primero debes generar:\n"
            f"output/indice_af.csv"
        )


def normalizar_df(df: pd.DataFrame) -> pd.DataFrame:
    df = df.rename(columns={k: v for k, v in RENAME_MAP.items() if k in df.columns})

    if "cod_dist" not in df.columns:
        raise ValueError("El archivo indice_af.csv no tiene columna cod_dist")

    df["cod_dist"] = df["cod_dist"].astype(str).str.zfill(6)

    if "n_privaciones" in df.columns:
        df["n_privaciones"] = (
            pd.to_numeric(df["n_privaciones"], errors="coerce")
            .fillna(0)
            .astype(int)
        )

    if "total_pers" in df.columns:
        df["total_pers"] = pd.to_numeric(df["total_pers"], errors="coerce")

    if "poblacion" in df.columns and "total_pers" not in df.columns:
        df["total_pers"] = pd.to_numeric(df["poblacion"], errors="coerce")

    if "impacto" not in df.columns and {"n_privaciones", "total_pers"}.issubset(df.columns):
        df["impacto"] = df["n_privaciones"] * df["total_pers"]

    return df


def agregar_servicios_y_dimensiones(df: pd.DataFrame) -> pd.DataFrame:
    priv_cols = [c for c in SERVICIOS if c in df.columns]

    for col in priv_cols:
        df[col] = (
            pd.to_numeric(df[col], errors="coerce")
            .fillna(0)
            .astype(int)
        )

    def servicios_row(row):
        faltantes = [
            nombre
            for col, nombre in SERVICIOS.items()
            if col in row.index and row[col] == 1
        ]
        return ", ".join(faltantes)

    def dimensiones_row(row):
        faltantes = []

        for dim, cols in DIMENSIONES.items():
            cols_validas = [c for c in cols if c in row.index]

            if cols_validas and row[cols_validas].sum() > 0:
                faltantes.append(dim)

        return ", ".join(faltantes)

    df["servicios_faltantes"] = df.apply(servicios_row, axis=1)
    df["dimensiones_faltantes"] = df.apply(dimensiones_row, axis=1)

    return df


def preparar_geometria() -> gpd.GeoDataFrame:
    print("Leyendo ig_distrito.csv...")
    df_ig = limpiar_ig(IG_PATH, verbose=True)

    print("Convirtiendo WKT a GeoDataFrame...")
    gdf = to_geopandas(df_ig)

    gdf["cod_dist"] = gdf["cod_dist"].astype(str).str.zfill(6)

    print(f"CRS: {gdf.crs}")
    print(f"Filas geometría: {len(gdf)}")
    print(f"cod_dist únicos geometría: {gdf['cod_dist'].nunique()}")

    return gdf


def preparar_indice() -> pd.DataFrame:
    print("Leyendo indice_af.csv...")
    df = pd.read_csv(INDICE_PATH)

    print(f"Filas índice: {len(df)}")
    print(f"Columnas índice: {len(df.columns)}")

    df = normalizar_df(df)
    df = agregar_servicios_y_dimensiones(df)

    return df


# ============================================================================
# MAIN
# ============================================================================

def main():
    print("=" * 80)
    print("GENERANDO DATOS WEB GEOJSON + JSON")
    print("=" * 80)

    validar_archivos()

    gdf = preparar_geometria()
    df = preparar_indice()

    print("Haciendo merge geometría + índice...")
    gdf_web = gdf.merge(df, on="cod_dist", how="left")

    n_sin_match = gdf_web["n_privaciones"].isna().sum() if "n_privaciones" in gdf_web.columns else None

    print(f"Filas después del merge: {len(gdf_web)}")
    print(f"Sin match índice: {n_sin_match}")

    print("Simplificando geometrías para web...")
    gdf_web["geometry"] = gdf_web["geometry"].simplify(
        tolerance=0.005,
        preserve_topology=True,
    )

    cols_web_base = [
        "cod_dist",
        "nom_dist",
        "nom_dpto",
        "nom_prov",
        "nom_dist_ig",
        "nom_dpto_ig",
        "nom_prov_ig",
        "capital",
        "clasificacion",
        "n_privaciones",
        "total_pers",
        "pct_nbi_real",
        "pct_nbi_predicho",
        "pct_sin_internet",
        "pct_ccpp_con_4g",
        "km_hospital",
        "km_secundaria",
        "n_estab_30km",
        "n_colegios_30km",
        "impacto",
        "tiene_tambo",
        "factor_dominante",
        "intervencion_recomendada",
        "servicios_faltantes",
        "dimensiones_faltantes",
        "geometry",
    ]

    priv_cols = [c for c in SERVICIOS if c in gdf_web.columns]

    cols_web = [c for c in cols_web_base if c in gdf_web.columns] + priv_cols
    cols_web = list(dict.fromkeys(cols_web))

    gdf_web = gdf_web[cols_web].copy()

    print("Guardando GeoJSON para React...")
    gdf_web.to_file(GEOJSON_OUT, driver="GeoJSON")

    print("Guardando indice_af.json para React...")
    df.to_json(INDICE_JSON_OUT, orient="records", force_ascii=False)

    print()
    print("✅ Archivos generados correctamente:")
    print(f"   {GEOJSON_OUT}")
    print(f"   {INDICE_JSON_OUT}")
    print()
    print(f"GeoJSON filas: {len(gdf_web)}")
    print(f"GeoJSON columnas: {len(gdf_web.columns)}")
    print(f"Columnas exportadas:")
    for c in gdf_web.columns:
        print(f"   - {c}")


if __name__ == "__main__":
    main()