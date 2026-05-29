"""
limpieza_ig.py — Polígonos distritales del INEI Censo 2017

Este dataset desbloquea las dos cosas más importantes del Bloque A:
    1. Centroides distritales -> calcular km_hospital, km_colegio (KDTree)
    2. Mapa coroplético del Perú coloreado por privación territorial

AVISO CRÍTICO sobre el formato:
    El WKT de este archivo viene en orden NO ESTÁNDAR 'lat lon' (ej.
    "-7.365 -79.463" significa lat=-7.365, lon=-79.463). El estándar WKT
    internacional es 'lon lat'. Si parseas directamente con shapely sin
    hacer swap, los centroides saldrán invertidos.

    Este módulo maneja el swap automáticamente.

Uso:
    from limpieza_ig import limpiar_ig, calcular_centroides, merge_centroides_con_distrital

    df_ig = limpiar_ig('data/ig_distrito.csv')
    df_centroides = calcular_centroides(df_ig)
    df_full = merge_centroides_con_distrital(df_full, df_centroides)
"""

import polars as pl
import pandas as pd
import re


# ============================================================================
# CONFIG
# ============================================================================

COLS_IG = [
    'ubigeo',       # JOIN KEY con cod_dist (Int64, 6 dígitos)
    'nombdep',      # nombre departamento
    'nombprov',     # nombre provincia
    'nombdist',     # nombre distrito
    'capital',      # capital del distrito
    'geom',         # WKT MULTIPOLYGON en orden 'lat lon' (no estándar)
]

RENAME_IG = {
    'ubigeo':   'cod_dist',
    'nombdep':  'nom_dpto_ig',     # _ig para distinguir del distrital
    'nombprov': 'nom_prov_ig',
    'nombdist': 'nom_dist_ig',
}

LAT_PERU = (-18.5, 0.0)
LON_PERU = (-82.0, -68.0)


# ============================================================================
# LIMPIEZA
# ============================================================================

def limpiar_ig(path, verbose=True):
    """
    Carga el CSV de polígonos distritales y selecciona columnas útiles.

    Returns:
        pl.DataFrame con 1,874 distritos (esperado), 6 columnas
    """
    df = pl.read_csv(path)
    n_inicial = len(df)
    n_cols_inicial = len(df.columns)

    # Validar columnas
    faltantes = [c for c in COLS_IG if c not in df.columns]
    if faltantes:
        raise ValueError(f"Columnas faltantes en ig_distrito: {faltantes}")

    df = df.select(COLS_IG)
    df = df.rename(RENAME_IG)

    # Validaciones
    assert df['cod_dist'].null_count() == 0, "cod_dist con nulls"
    assert df['cod_dist'].n_unique() == len(df), "cod_dist duplicados"
    assert df['geom'].null_count() == 0, "geometrías con nulls"

    if verbose:
        print(f"[ig] inicial:           {n_inicial:>5} × {n_cols_inicial} cols")
        print(f"[ig] tras corte:        {len(df):>5} × {len(df.columns)} cols")
        print(f"[ig] cod_dist únicos:   {df['cod_dist'].n_unique():>5}")
        print(f"[ig] departamentos:     {df['nom_dpto_ig'].n_unique():>5}")

    return df


# ============================================================================
# CÁLCULO DE CENTROIDES
# ============================================================================

# Regex que captura un par 'lat lon' (números con decimal, posiblemente negativos)
_PATRON_COORD = re.compile(r'(-?\d+\.\d+)\s+(-?\d+\.\d+)')


def centroide_aproximado(wkt_text):
    """
    Calcula el centroide promedio de todos los vértices del WKT.

    NOTA: este es el centroide ARITMÉTICO (promedio de vértices),
    no el centroide GEOMÉTRICO (centro de masa del polígono).
    Para distritos peruanos la diferencia es pequeña (<5 km en distritos
    grandes) y es suficiente para alimentar el KDTree.

    Si se necesita el centroide geométrico exacto, usar geopandas:
        gdf = pl_to_geopandas(df_ig)
        gdf['centroide'] = gdf['geom'].centroid

    El WKT viene en orden 'lat lon' (no estándar), así que el primer
    número de cada par es lat y el segundo es lon.
    """
    pares = _PATRON_COORD.findall(wkt_text)
    if not pares:
        return None, None
    lats = [float(p[0]) for p in pares]
    lons = [float(p[1]) for p in pares]
    return sum(lats) / len(lats), sum(lons) / len(lons)


def calcular_centroides(df_ig, verbose=True):
    """
    Para cada distrito en df_ig, calcula el centroide aproximado.

    Returns:
        pl.DataFrame con [cod_dist, lat_centroide, lon_centroide]
    """
    # Aplicar centroide_aproximado a cada fila
    centroides = []
    for cod, wkt in zip(df_ig['cod_dist'].to_list(), df_ig['geom'].to_list()):
        lat, lon = centroide_aproximado(wkt)
        centroides.append((cod, lat, lon))

    out = pl.DataFrame(
        centroides,
        schema=['cod_dist', 'lat_centroide', 'lon_centroide'],
        orient='row',
    )

    # Validaciones
    invalid_lat = out.filter(
        ~pl.col('lat_centroide').is_between(LAT_PERU[0], LAT_PERU[1])
    )
    invalid_lon = out.filter(
        ~pl.col('lon_centroide').is_between(LON_PERU[0], LON_PERU[1])
    )
    if len(invalid_lat) > 0 or len(invalid_lon) > 0:
        print(f"⚠️  Centroides fuera de Perú: lat={len(invalid_lat)}, lon={len(invalid_lon)}")
        # Mostrar los problemáticos para debug
        if len(invalid_lat) > 0:
            print(invalid_lat.head(3))

    if verbose:
        print(f"[centroides] calculados:        {len(out):>5}")
        print(f"[centroides] rango lat:         "
              f"[{out['lat_centroide'].min():.2f}, {out['lat_centroide'].max():.2f}]")
        print(f"[centroides] rango lon:         "
              f"[{out['lon_centroide'].min():.2f}, {out['lon_centroide'].max():.2f}]")

    return out


# ============================================================================
# MERGE CON DISTRITAL
# ============================================================================

def merge_centroides_con_distrital(df_distrital, df_centroides, verbose=True):
    """
    Left join de centroides al dataframe distrital (pandas).

    Args:
        df_distrital:   pandas DataFrame (output de limpiar_distrital o df_full)
        df_centroides:  polars DataFrame (output de calcular_centroides)
    Returns:
        pandas DataFrame + columnas lat_centroide, lon_centroide
    """
    df_cent_pd = df_centroides.to_pandas()
    out = df_distrital.merge(df_cent_pd, on='cod_dist', how='left')

    if verbose:
        n_sin = out['lat_centroide'].isna().sum()
        print(f"[merge_ig] shape final:                  {out.shape}")
        print(f"[merge_ig] distritos sin centroide:      {n_sin}")
        if n_sin > 0:
            print(f"  → estos no tendrán km_hospital ni km_colegio")

    return out


# ============================================================================
# OPCIONAL: conversión a GeoDataFrame para el mapa coroplético
# ============================================================================

def to_geopandas(df_ig):
    """
    Convierte el polars DataFrame a un GeoDataFrame de geopandas
    para mapa coroplético y operaciones geométricas precisas.

    Requiere: pip install geopandas shapely

    Hace el swap lat-lon -> lon-lat para cumplir con el estándar WKT.
    """
    try:
        import geopandas as gpd
        from shapely import wkt
    except ImportError:
        raise ImportError(
            "Para usar to_geopandas() necesitas:\n"
            "    pip install geopandas shapely"
        )

    df_pd = df_ig.to_pandas()

    # Swap lat-lon -> lon-lat en el WKT para que shapely lo interprete bien
    def swap_coords(wkt_text):
        return _PATRON_COORD.sub(r'\2 \1', wkt_text)

    df_pd['geom_wkt_std'] = df_pd['geom'].apply(swap_coords)
    df_pd['geometry'] = df_pd['geom_wkt_std'].apply(wkt.loads)
    gdf = gpd.GeoDataFrame(df_pd, geometry='geometry', crs='EPSG:4326')

    return gdf.drop(columns=['geom', 'geom_wkt_std'])


# ============================================================================
# MAIN — validación con muestra
# ============================================================================

if __name__ == '__main__':
    print("=" * 70)
    print("LIMPIEZA IG (polígonos distritales) — GeoTón Perú 2026")
    print("=" * 70)

    # Probar con muestra
    PATH = '/mnt/user-data/uploads/ig_distrito_sample_100.csv'
    df_ig = limpiar_ig(PATH)

    print()
    df_cent = calcular_centroides(df_ig)

    print(f"\n--- MUESTRA centroides ---")
    print(df_cent.head(10))

    print(f"\n--- Sanity check: matchear con nombres ---")
    join = df_ig.join(df_cent, on='cod_dist')
    print(
        join.select(['nom_dpto_ig', 'nom_dist_ig', 'lat_centroide', 'lon_centroide'])
            .head(5)
    )
