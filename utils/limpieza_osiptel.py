"""
limpieza_osiptel.py — Limpieza y agregación distrital de cobertura móvil OSIPTEL

Datos: Cobertura_móvil_por_empresa_operadora.csv (51,366 filas)
Granularidad original: CCPP × Empresa (long format)
Período: marzo 2023 (PERIODO=202303)
Operadoras: 4 (Viettel/Bitel, Telefónica/Movistar, América Móvil/Claro, Entel)

Para el pipeline GeoTón necesitamos features a NIVEL DISTRITAL, así que el
módulo hace una doble agregación:

    Granularidad        Agregación               Resultado
    ─────────────       ─────────────            ────────────────
    CCPP × Empresa  ->  max/sum por CCPP    ->   CCPP único con flags
    CCPP            ->  mean/count por dist ->   distrito con % cobertura

Hallazgo importante:
    1,664 distritos reportan cobertura, pero 211 distritos del padrón
    INEI NO tienen NINGÚN reporte OSIPTEL. Estos son los desiertos digitales
    extremos. Al hacer el merge LEFT, esos 211 se imputan a 0% (la ausencia
    de reporte ES la señal).

Uso:
    from limpieza_osiptel import (
        limpiar_osiptel,
        features_osiptel_por_distrito,
        merge_osiptel_con_distrital,
    )
    df_ops = limpiar_osiptel('/mnt/project/Cobertura_móvil_por_empresa_operadora.csv')
    df_ops_dist = features_osiptel_por_distrito(df_ops)
    df_full = merge_osiptel_con_distrital(df_full_pandas, df_ops_dist)
"""

import pandas as pd
import numpy as np


# ============================================================================
# CONFIG
# ============================================================================

# Columnas a mantener (de 25)
COLS_OSIPTEL = [
    # Identificadores geográficos
    'UBIGEO_DISTRITO',    # 6 dígitos (int64) — JOIN KEY con cod_dist
    'UBIGEO_CCPP',        # 10 dígitos — identifica el centro poblado
    'DEPARTAMENTO', 'PROVINCIA', 'DISTRITO',
    'CENTRO_POBLADO',
    'LATITUD', 'LONGITUD',
    # Empresa
    'EMPRESA_OPERADORA',
    # Cobertura por tecnología (0/1)
    '2G', '3G', '4G', '5G',
    # Servicio de internet (1 = velocidades >1 Mbps disponibles)
    'MÁS_DE_1_MBPS',
    # Infraestructura 4G (más relevante que 2G/3G para la tesis)
    'CANT_EB_4G',
]

# Mapeo a snake_case para consistencia con los otros módulos
RENAME_OSIPTEL = {
    'UBIGEO_DISTRITO':   'cod_dist',
    'UBIGEO_CCPP':       'cod_ccpp',
    'DEPARTAMENTO':      'departamento',
    'PROVINCIA':         'provincia',
    'DISTRITO':          'distrito',
    'CENTRO_POBLADO':    'centro_poblado',
    'LATITUD':           'lat',
    'LONGITUD':          'lon',
    'EMPRESA_OPERADORA': 'empresa',
    '2G':                'cob_2g',
    '3G':                'cob_3g',
    '4G':                'cob_4g',
    '5G':                'cob_5g',
    'MÁS_DE_1_MBPS':     'internet_rapido',
    'CANT_EB_4G':        'n_estaciones_4g',
}

# Rango Perú para validar coordenadas
LAT_PERU = (-18.5, 0.0)
LON_PERU = (-82.0, -68.0)


# ============================================================================
# LIMPIEZA
# ============================================================================

def limpiar_osiptel(path='/mnt/project/Cobertura_móvil_por_empresa_operadora.csv',
                    verbose=True):
    """
    Carga y limpia el CSV de cobertura móvil OSIPTEL.

    Pasos:
        1. Carga con encoding cp1252 y sep=';'
        2. Selecciona 16 columnas relevantes (de 25)
        3. Renombra a snake_case
        4. Valida tipos, nulls y rango de coordenadas

    NOTA: una fila = un reporte (CCPP × Empresa). Si un CCPP tiene
          cobertura de 3 operadores, aparecen 3 filas.

    Returns:
        pd.DataFrame con ~51,366 reportes (CCPP × Empresa) limpios
    """
    df = pd.read_csv(path, encoding='cp1252', sep=';', low_memory=False)
    n_inicial = len(df)
    n_cols_inicial = len(df.columns)

    # 1. Validar período (los datos son de un único corte)
    periodos = df['PERIODO'].unique()
    if len(periodos) > 1:
        print(f"⚠️  Múltiples períodos en el CSV: {periodos}")

    # 2. Seleccionar columnas
    faltantes = [c for c in COLS_OSIPTEL if c not in df.columns]
    if faltantes:
        raise ValueError(f"Columnas faltantes en OSIPTEL: {faltantes}")
    df = df[COLS_OSIPTEL].copy()

    # 3. Renombrar a snake_case
    df = df.rename(columns=RENAME_OSIPTEL)

    # 4. Validaciones
    assert df['cod_dist'].notna().all(), "cod_dist con nulls"
    assert df['cod_ccpp'].notna().all(), "cod_ccpp con nulls"
    assert df['lat'].between(LAT_PERU[0], LAT_PERU[1]).all(), \
        "Latitudes fuera de rango Perú"
    assert df['lon'].between(LON_PERU[0], LON_PERU[1]).all(), \
        "Longitudes fuera de rango Perú"
    # Las flags de cobertura deben ser 0/1
    for c in ['cob_2g', 'cob_3g', 'cob_4g', 'cob_5g', 'internet_rapido']:
        assert df[c].isin([0, 1]).all(), f"{c} tiene valores ≠ 0/1"

    if verbose:
        print(f"[osiptel] inicial:                    {n_inicial:>6}  ({n_cols_inicial} cols)")
        print(f"[osiptel] tras corte:                 {len(df):>6}  ({len(df.columns)} cols)")
        print(f"[osiptel] período:                    {periodos[0]}")
        print(f"[osiptel] CCPP únicos:                {df['cod_ccpp'].nunique():>6}")
        print(f"[osiptel] distritos con reporte:      {df['cod_dist'].nunique():>6} / 1,874")
        print(f"[osiptel] operadoras:                 "
              f"{', '.join(df['empresa'].unique())}")
        print(f"[osiptel] cobertura por tecnología (reportes con valor=1):")
        for c, label in [('cob_2g', '2G'), ('cob_3g', '3G'),
                         ('cob_4g', '4G'), ('cob_5g', '5G')]:
            n = df[c].sum()
            print(f"   {label}:  {n:>6} ({100*n/len(df):.1f}%)")

    return df


# ============================================================================
# AGREGACIÓN: CCPP × Empresa -> CCPP único -> Distrito
# ============================================================================

def features_osiptel_por_distrito(df_ops, verbose=True):
    """
    Construye features a nivel DISTRITAL desde reportes CCPP × Empresa.

    Hace una doble agregación:
        1. CCPP × Empresa -> CCPP único:
            tiene_Xg = max() — al menos 1 operador con cobertura
            n_ops_Xg = sum() — cuántos operadores tienen esa tecnología
        2. CCPP -> Distrito:
            pct_ccpp_con_Xg = mean(tiene_Xg) * 100 — % CCPP del distrito con cobertura
            n_operadores_promedio = mean(n_ops_*) — competencia de mercado

    Features generadas por distrito:
        n_ccpp_osiptel              CCPP únicos con algún reporte
        pct_ccpp_con_2g/3g/4g/5g    % CCPP del distrito con esa cobertura
        pct_ccpp_internet_rapido    % CCPP con >1 Mbps de algún operador
        n_operadores_promedio_4g    operadores con 4G promedio por CCPP (competencia)
        total_estaciones_4g         suma de estaciones base 4G del distrito
        tiene_4g                    bool: al menos un CCPP del distrito con 4G

    Returns:
        pd.DataFrame con un distrito por fila (cod_dist) y métricas agregadas
    """
    # === Paso 1: CCPP × Empresa -> CCPP único ===
    # Para cada CCPP: ¿algún operador tiene 4G? ¿cuántos lo tienen?
    ccpp = df_ops.groupby('cod_ccpp').agg(
        cod_dist=('cod_dist', 'first'),
        # ¿al menos 1 operador con esa tech? (max sobre binarios)
        tiene_2g=('cob_2g', 'max'),
        tiene_3g=('cob_3g', 'max'),
        tiene_4g=('cob_4g', 'max'),
        tiene_5g=('cob_5g', 'max'),
        tiene_internet_rapido=('internet_rapido', 'max'),
        # ¿cuántos operadores tienen esa tech? (sum sobre binarios)
        n_ops_4g=('cob_4g', 'sum'),
        # infraestructura agregada
        estaciones_4g=('n_estaciones_4g', 'sum'),
    ).reset_index()

    # === Paso 2: CCPP -> Distrito ===
    dist = ccpp.groupby('cod_dist').agg(
        n_ccpp_osiptel=('cod_ccpp', 'count'),
        pct_ccpp_con_2g=('tiene_2g', lambda x: 100 * x.mean()),
        pct_ccpp_con_3g=('tiene_3g', lambda x: 100 * x.mean()),
        pct_ccpp_con_4g=('tiene_4g', lambda x: 100 * x.mean()),
        pct_ccpp_con_5g=('tiene_5g', lambda x: 100 * x.mean()),
        pct_ccpp_internet_rapido=('tiene_internet_rapido',
                                  lambda x: 100 * x.mean()),
        n_operadores_promedio_4g=('n_ops_4g', 'mean'),
        total_estaciones_4g=('estaciones_4g', 'sum'),
    ).reset_index()

    # Bool útil para Alkire-Foster
    dist['tiene_4g'] = dist['pct_ccpp_con_4g'] > 0

    # Redondeo razonable
    for c in dist.columns:
        if c.startswith('pct_') or c.startswith('n_operadores'):
            dist[c] = dist[c].round(2)

    if verbose:
        print(f"[osiptel_agg] distritos con reporte:    {len(dist):>5}")
        print(f"[osiptel_agg] distritos sin 4G en ningún CCPP: "
              f"{(dist['pct_ccpp_con_4g'] == 0).sum():>5}")
        print(f"[osiptel_agg] media pct_ccpp_con_4g:    "
              f"{dist['pct_ccpp_con_4g'].mean():>5.1f}%")
        print(f"[osiptel_agg] media operadores 4G/CCPP: "
              f"{dist['n_operadores_promedio_4g'].mean():>5.2f}")

    return dist


# ============================================================================
# MERGE CON DISTRITAL
# ============================================================================

def merge_osiptel_con_distrital(df_distrital, df_ops_dist, verbose=True):
    """
    Left join del agregado distrital de OSIPTEL al dataframe distrital.

    Maneja los 211 distritos sin reporte OSIPTEL imputándolos a 0:
        La AUSENCIA de reporte es información. Significa que ningún
        operador declaró cobertura en ese distrito -> el "desierto digital"
        extremo. NO es null, es 0% de cobertura.

    Args:
        df_distrital:  pandas DataFrame (output de limpiar_distrital o df_full)
        df_ops_dist:   pandas DataFrame (output de features_osiptel_por_distrito)
    Returns:
        df_distrital + 9 columnas de OSIPTEL
    """
    out = df_distrital.merge(df_ops_dist, on='cod_dist', how='left')

    # Imputar: los distritos sin reporte OSIPTEL son 0% cobertura
    cols_pct = [c for c in df_ops_dist.columns if c.startswith('pct_')]
    cols_n = ['n_ccpp_osiptel', 'n_operadores_promedio_4g', 'total_estaciones_4g']
    for c in cols_pct + cols_n:
        if c in out.columns:
            out[c] = out[c].fillna(0)

    if 'tiene_4g' in out.columns:
        out['tiene_4g'] = out['tiene_4g'].fillna(False)

    if verbose:
        n_sin = (out['n_ccpp_osiptel'] == 0).sum()
        n_4g = out['tiene_4g'].sum() if 'tiene_4g' in out.columns else 0
        print(f"[merge_osiptel] shape final:                   {out.shape}")
        print(f"[merge_osiptel] distritos sin reporte (= 0%):  {n_sin:>5}")
        print(f"[merge_osiptel] distritos con algo de 4G:      {n_4g:>5} "
              f"({100*n_4g/len(out):.1f}%)")

    return out


# ============================================================================
# MAIN — validación
# ============================================================================

if __name__ == '__main__':
    print("=" * 70)
    print("LIMPIEZA OSIPTEL — GeoTón Perú 2026")
    print("=" * 70)

    df_ops = limpiar_osiptel()
    print()
    df_ops_dist = features_osiptel_por_distrito(df_ops)

    print(f"\n--- MUESTRA del agregado distrital ---")
    print(df_ops_dist.head(5).to_string(index=False))

    # Demo opcional del merge: solo si limpieza.py está accesible.
    # No es crítico — el merge real lo hace el usuario en su notebook.
    try:
        from limpieza import limpiar_distrital
        print("\n--- MERGE con distrital ---")
        df_dis = limpiar_distrital(verbose=False)
        df_full = merge_osiptel_con_distrital(df_dis, df_ops_dist)

        print(f"\n--- TOP 10 distritos más desconectados (4G) ---")
        cols = ['nom_dpto', 'nom_dist', 'pct_nbi', 'pct_sin_internet',
                'n_ccpp_osiptel', 'pct_ccpp_con_4g']
        print(df_full.nsmallest(10, 'pct_ccpp_con_4g')[cols].to_string(index=False))
    except (ImportError, ModuleNotFoundError, FileNotFoundError) as e:
        print(f"\n(Demo del merge con distrital omitida: limpieza.py "
              f"no encontrado en este entorno. Esto NO es un error — "
              f"el merge real lo haces en tu notebook combinando ambos módulos.)")
