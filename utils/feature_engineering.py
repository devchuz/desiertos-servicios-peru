"""
feature_engineering.py — Variables derivadas para el modelo del Bloque B

Genera 4 grupos de features adicionales a partir de la tabla maestra distrital:

  1. DISTANCIAS (KDTree/BallTree con métrica Haversine):
       km_hospital, km_salud_cercano, km_colegio, km_secundaria
       n_estab_30km, n_colegios_30km

  2. DISPERSIÓN TERRITORIAL (desde CCPP de OSIPTEL):
       std_lat_ccpp, std_lon_ccpp        — qué tan dispersos están los CCPP
       n_ccpp_distrito                    — cantidad de CCPP del distrito
       dist_promedio_ccpp_km              — distancia media entre CCPP

  3. RATIOS PER CAPITA:
       habitantes_por_estab_salud
       habitantes_por_hospital
       habitantes_por_secundaria
       habitantes_por_escuela

  4. INTERACCIONES (variables compuestas que NO usan el target):
       indice_aislamiento  = km_hospital * pct_sin_internet / 100
       ratio_rural         = pct_rural_escuelas * pct_sin_agua / 100

NOTA TÉCNICA: para distancias geográficas usamos BallTree con métrica Haversine.
NO usamos cKDTree con grados euclidianos porque 1° de longitud en Lima ≠ 1° en
Loreto, y eso introduce sesgo sistemático en distritos selva/sierra.

Uso:
    from feature_engineering import enriquecer_features
    df_full = enriquecer_features(df_full, df_sal, df_esc, df_ops)
"""

import numpy as np
import pandas as pd
from sklearn.neighbors import BallTree


# Radio de la Tierra en km
RADIO_TIERRA_KM = 6371.0

# Categorías de hospital (>= II-1) según MINSA
HOSP_CATS = ['II-1', 'II-2', 'II-E', 'III-1', 'III-2', 'III-E']


# ============================================================================
# DISTANCIAS GEOGRÁFICAS
# ============================================================================

def _balltree_haversine(coords_lat_lon):
    """
    Construye un BallTree con métrica Haversine.
    Las coordenadas deben pasarse en GRADOS — la función las convierte a radianes.
    """
    return BallTree(np.radians(coords_lat_lon), metric='haversine')


def _distancia_y_radio(tree, query_coords_grados, radio_km=30):
    """
    Para cada punto en query_coords (grados), devuelve:
        dist_min_km:  distancia al punto más cercano del tree (en km)
        n_en_radio:   cantidad de puntos del tree dentro del radio (en km)
    """
    query_rad = np.radians(query_coords_grados)

    # Distancia al más cercano
    dist_rad, _ = tree.query(query_rad, k=1)
    dist_km = (dist_rad.ravel() * RADIO_TIERRA_KM)

    # Cantidad dentro del radio
    radio_rad = radio_km / RADIO_TIERRA_KM
    indices_en_radio = tree.query_radius(query_rad, r=radio_rad, count_only=True)

    return dist_km, indices_en_radio.astype(int)


def features_distancias_salud(df_centroides, df_salud, verbose=True):
    """
    Calcula features de distancia a establecimientos de salud por distrito.

    Args:
        df_centroides: pandas DF con [cod_dist, lat_centroide, lon_centroide]
        df_salud:      pandas DF con [cod_dist, lat, lon, es_hospital]

    Returns:
        pandas DF con [cod_dist, km_salud_cercano, km_hospital, n_estab_30km]
    """
    # Filtrar centroides válidos (no nulos)
    mask = df_centroides[['lat_centroide', 'lon_centroide']].notna().all(axis=1)
    centros = df_centroides[mask].copy()
    coords_centros = centros[['lat_centroide', 'lon_centroide']].values

    # KDTrees
    coords_estab = df_salud[['lat', 'lon']].values
    tree_estab = _balltree_haversine(coords_estab)

    df_hosp = df_salud[df_salud['es_hospital']]
    coords_hosp = df_hosp[['lat', 'lon']].values
    tree_hosp = _balltree_haversine(coords_hosp)

    # Distancia a establecimiento más cercano + densidad en 30 km
    km_salud, n_30km = _distancia_y_radio(tree_estab, coords_centros, radio_km=30)
    # Distancia a hospital más cercano
    km_hosp, _ = _distancia_y_radio(tree_hosp, coords_centros, radio_km=30)

    out = pd.DataFrame({
        'cod_dist': centros['cod_dist'].values,
        'km_salud_cercano': km_salud.round(2),
        'km_hospital': km_hosp.round(2),
        'n_estab_30km': n_30km,
    })

    if verbose:
        print(f"[dist_salud] distritos procesados:    {len(out):>5}")
        print(f"[dist_salud] km_salud_cercano: "
              f"media={out['km_salud_cercano'].mean():.1f}, "
              f"max={out['km_salud_cercano'].max():.1f}")
        print(f"[dist_salud] km_hospital:      "
              f"media={out['km_hospital'].mean():.1f}, "
              f"max={out['km_hospital'].max():.1f}")
        print(f"[dist_salud] n_estab_30km:     "
              f"media={out['n_estab_30km'].mean():.1f}, "
              f"max={out['n_estab_30km'].max()}")

    return out


def features_distancias_escuelas(df_centroides, df_escuelas, verbose=True):
    """
    Calcula features de distancia a escuelas por distrito.

    Args:
        df_centroides: pandas DF con [cod_dist, lat_centroide, lon_centroide]
        df_escuelas:   Polars DF con [cod_dist, lat, lon, es_secundaria, es_regular]
                       (convertido a pandas internamente)

    Returns:
        pandas DF con [cod_dist, km_colegio, km_secundaria, n_colegios_30km]
    """
    # Soportar Polars o pandas
    if hasattr(df_escuelas, 'to_pandas'):
        df_esc = df_escuelas.to_pandas()
    else:
        df_esc = df_escuelas

    # Solo escuelas regulares (EBR) para "colegio más cercano"
    df_reg = df_esc[df_esc['es_regular']]
    coords_reg = df_reg[['lat', 'lon']].values
    tree_reg = _balltree_haversine(coords_reg)

    # Solo secundarias
    df_sec = df_esc[df_esc['es_secundaria']]
    coords_sec = df_sec[['lat', 'lon']].values
    tree_sec = _balltree_haversine(coords_sec)

    # Centroides
    mask = df_centroides[['lat_centroide', 'lon_centroide']].notna().all(axis=1)
    centros = df_centroides[mask]
    coords_centros = centros[['lat_centroide', 'lon_centroide']].values

    km_col, n_30km = _distancia_y_radio(tree_reg, coords_centros, radio_km=30)
    km_sec, _ = _distancia_y_radio(tree_sec, coords_centros, radio_km=30)

    out = pd.DataFrame({
        'cod_dist': centros['cod_dist'].values,
        'km_colegio': km_col.round(2),
        'km_secundaria': km_sec.round(2),
        'n_colegios_30km': n_30km,
    })

    if verbose:
        print(f"[dist_esc] distritos procesados:    {len(out):>5}")
        print(f"[dist_esc] km_colegio:     media={out['km_colegio'].mean():.1f}, "
              f"max={out['km_colegio'].max():.1f}")
        print(f"[dist_esc] km_secundaria:  media={out['km_secundaria'].mean():.1f}, "
              f"max={out['km_secundaria'].max():.1f}")

    return out


# ============================================================================
# DISPERSIÓN TERRITORIAL (desde CCPP de OSIPTEL)
# ============================================================================

def features_dispersion_ccpp(df_osiptel, verbose=True):
    """
    Calcula dispersión geográfica de los CCPP dentro de cada distrito.

    Un distrito con CCPP muy dispersos es más 'rural' geográficamente.
    Un distrito concentrado es más urbano/compacto.

    Args:
        df_osiptel: pandas DF de OSIPTEL con [cod_dist, lat, lon, cod_ccpp]

    Returns:
        pandas DF con [cod_dist, n_ccpp_distrito, std_lat_ccpp, std_lon_ccpp,
                        radio_distrito_km]
    """
    # CCPP únicos por distrito (no repetir por operador)
    ccpp = df_osiptel.drop_duplicates('cod_ccpp')[['cod_dist', 'cod_ccpp', 'lat', 'lon']]

    agg = ccpp.groupby('cod_dist').agg(
        n_ccpp_distrito=('cod_ccpp', 'count'),
        lat_media=('lat', 'mean'),
        lon_media=('lon', 'mean'),
        std_lat_ccpp=('lat', 'std'),
        std_lon_ccpp=('lon', 'std'),
    ).reset_index()

    # "Radio del distrito" en km, aproximado vía Haversine al promedio de std
    # std en grados ≈ std en km dividiendo por 111
    agg['radio_distrito_km'] = (
        ((agg['std_lat_ccpp'].fillna(0) ** 2 +
          agg['std_lon_ccpp'].fillna(0) ** 2) ** 0.5) * 111
    ).round(2)

    # Limpieza: distritos con 1 solo CCPP tienen std=NaN → 0
    agg['std_lat_ccpp'] = agg['std_lat_ccpp'].fillna(0).round(4)
    agg['std_lon_ccpp'] = agg['std_lon_ccpp'].fillna(0).round(4)

    # Solo columnas útiles
    agg = agg[['cod_dist', 'n_ccpp_distrito', 'std_lat_ccpp',
               'std_lon_ccpp', 'radio_distrito_km']]

    if verbose:
        print(f"[dispersion] distritos:             {len(agg):>5}")
        print(f"[dispersion] media n_ccpp:          {agg['n_ccpp_distrito'].mean():.1f}")
        print(f"[dispersion] max n_ccpp:            {agg['n_ccpp_distrito'].max()}")
        print(f"[dispersion] radio promedio (km):   {agg['radio_distrito_km'].mean():.1f}")

    return agg


# ============================================================================
# RATIOS PER CAPITA
# ============================================================================

def features_ratios(df_full, verbose=True):
    """
    Calcula ratios de servicios per cápita. Útil para distinguir distritos
    pequeños bien servidos de distritos grandes mal servidos.

    Espera que df_full tenga:
        total_pers, n_estab_salud, n_hospitales, n_secundarias, n_escuelas

    Returns:
        df_full con 4 columnas nuevas
    """
    df = df_full.copy()

    # Usamos max(1, x) para evitar divisiones por cero
    df['habitantes_por_estab_salud'] = (
        df['total_pers'] / df['n_estab_salud'].clip(lower=1)
    ).round(0)

    df['habitantes_por_hospital'] = (
        df['total_pers'] / df['n_hospitales'].clip(lower=1)
    ).round(0)

    df['habitantes_por_secundaria'] = (
        df['total_pers'] / df['n_secundarias'].clip(lower=1)
    ).round(0)

    df['habitantes_por_escuela'] = (
        df['total_pers'] / df['n_escuelas'].clip(lower=1)
    ).round(0)

    if verbose:
        print(f"[ratios] habitantes_por_estab_salud: "
              f"mediana={df['habitantes_por_estab_salud'].median():.0f}")
        print(f"[ratios] habitantes_por_hospital:    "
              f"mediana={df['habitantes_por_hospital'].median():.0f}")
        print(f"[ratios] habitantes_por_secundaria:  "
              f"mediana={df['habitantes_por_secundaria'].median():.0f}")

    return df


# ============================================================================
# INTERACCIONES (variables compuestas)
# ============================================================================

def features_interacciones(df_full, verbose=True):
    """
    Crea variables compuestas que capturan combinaciones conceptuales
    relevantes para la tesis "desierto de servicios".

    Se calculan SOLO si las columnas componentes ya existen.

    NOTA: NO incluimos combinaciones que usen `pct_nbi` porque ES el TARGET
    del modelo y causarían data leakage (el modelo aprende la relación trivial
    target × constante y deja de usar las otras features).
    """
    df = df_full.copy()

    # 1. Índice de aislamiento físico+digital
    #    NO usa el target. Captura "ni cerca de hospital ni con internet".
    if 'km_hospital' in df.columns and 'pct_sin_internet' in df.columns:
        df['indice_aislamiento'] = (
            df['km_hospital'] * df['pct_sin_internet'] / 100
        ).round(2)

    # 2. Ratio rural (combinación de educación rural + sin agua)
    #    NO usa el target. Captura "zona rural sin servicios básicos".
    if 'pct_rural_escuelas' in df.columns and 'pct_sin_agua' in df.columns:
        df['ratio_rural'] = (
            df['pct_rural_escuelas'] * df['pct_sin_agua'] / 100
        ).round(2)

    nuevas = ['indice_aislamiento', 'ratio_rural']
    creadas = [c for c in nuevas if c in df.columns]

    if verbose:
        print(f"[interacciones] columnas creadas: {creadas}")
        for c in creadas:
            print(f"  {c}: media={df[c].mean():.2f}, max={df[c].max():.2f}")

    return df


# ============================================================================
# PIPELINE COMPLETO
# ============================================================================

def enriquecer_features(df_full, df_salud, df_escuelas, df_osiptel, verbose=True):
    """
    Pipeline end-to-end: aplica los 4 grupos de feature engineering en orden.

    Args:
        df_full:     tabla maestra distrital (output del notebook 1)
                     debe tener: cod_dist, lat_centroide, lon_centroide,
                                 total_pers, n_estab_salud, n_hospitales,
                                 n_escuelas, n_secundarias
        df_salud:    pandas DF (output de limpiar_salud)
        df_escuelas: polars DF (output de limpiar_escuelas)
        df_osiptel:  pandas DF (output de limpiar_osiptel)

    Returns:
        df_full enriquecido con ~13 columnas nuevas
    """
    if verbose:
        print("=" * 60)
        print("FEATURE ENGINEERING")
        print("=" * 60)

    # Extraer centroides
    df_centroides = df_full[['cod_dist', 'lat_centroide', 'lon_centroide']]

    # 1. Distancias
    if verbose: print("\n--- 1. Distancias (BallTree + Haversine) ---")
    f_salud = features_distancias_salud(df_centroides, df_salud, verbose=verbose)
    df_full = df_full.merge(f_salud, on='cod_dist', how='left')

    f_esc = features_distancias_escuelas(df_centroides, df_escuelas, verbose=verbose)
    df_full = df_full.merge(f_esc, on='cod_dist', how='left')

    # 2. Dispersión
    if verbose: print("\n--- 2. Dispersión territorial (CCPP de OSIPTEL) ---")
    f_disp = features_dispersion_ccpp(df_osiptel, verbose=verbose)
    df_full = df_full.merge(f_disp, on='cod_dist', how='left')

    # 3. Ratios
    if verbose: print("\n--- 3. Ratios per capita ---")
    df_full = features_ratios(df_full, verbose=verbose)

    # 4. Interacciones (van al final porque usan distancias del paso 1)
    if verbose: print("\n--- 4. Interacciones / variables compuestas ---")
    df_full = features_interacciones(df_full, verbose=verbose)

    if verbose:
        print(f"\n[FE] shape final: {df_full.shape}")
        print(f"[FE] nulos: {df_full.isna().sum().sum()}")

    return df_full