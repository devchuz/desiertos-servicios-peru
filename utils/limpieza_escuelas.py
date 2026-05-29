"""
limpieza_escuelas.py — Limpieza del padrón MINEDU de instituciones educativas

Construido en Polars por el tamaño del dataset completo (~80-100k filas).

Decisiones de limpieza documentadas:
  - Filtros aplicados:
      esta_val == 'Activo'                (descarta inactivos)
      form_valor == 'Escolarizado'        (descarta PRONOEIs / programas no esc.)
      nlatie y nlongie en rango Perú      (descarta coordenadas inválidas)
      nivmod_val no nulo
  - 50 columnas -> 17 (drop duplicados administrativos, IDs internos,
    contacto, UGEL, códigos numéricos redundantes)
  - Flags útiles agregadas:
      es_primaria, es_secundaria, es_inicial
      es_regular (EBR sin EBE, EBA, Técnico Productiva)
      es_publico (Sector Educación / Convenio vs privadas)
      area_rural (bool)

Uso:
    import polars as pl
    from limpieza_escuelas import limpiar_escuelas, features_escuelas_por_distrito

    df_esc = limpiar_escuelas('/ruta/al/padron_completo.parquet')
    df_esc_dist = features_escuelas_por_distrito(df_esc)
"""

import polars as pl


# ============================================================================
# CONFIG
# ============================================================================

# 17 columnas a mantener (de 50)
COLS_ESCUELAS = [
    # Identificadores
    'codmod',           # código modular único del local educativo
    'cod_local',        # código del local físico (puede tener varios CE)
    # División geográfica (formato consistente con otros datasets)
    'cod_dist', 'nom_dist',
    'cod_prov', 'nom_prov',
    'cod_dpto', 'nom_dpto',
    # Coordenadas (ya vienen como Float64)
    'nlatie', 'nlongie',
    # Características
    'cenedu',           # nombre del centro educativo
    'nivmod_val',       # nivel/modalidad (Primaria, Secundaria, Inicial, etc.)
    'esta_val',         # Activo / Inactivo
    'form_valor',       # Escolarizado / No Escolarizado
    'gesdep_val',       # gestión (Sector Educación, Convenio, Privada, ...)
    'areaval',          # Urbana / Rural
    'alt_cp',           # altitud del centro poblado (bonus narrativo)
]

# Niveles regulares (EBR) — los que entran al pipeline por defecto
NIVELES_REGULARES = ['Primaria', 'Secundaria', 'Inicial - Jardín', 'Inicial - Cuna-Jardín',
                     'Inicial - Cuna']

# Rango válido de coordenadas para Perú
LAT_PERU = (-18.5, 0.0)
LON_PERU = (-82.0, -68.0)


# ============================================================================
# LIMPIEZA
# ============================================================================

def limpiar_escuelas(path, verbose=True):
    """
    Carga y limpia el padrón MINEDU de instituciones educativas.

    Args:
        path: ruta al archivo (.parquet, .csv, .xlsx, .xls)
        verbose: imprime estadísticas de validación

    Returns:
        pl.DataFrame con escuelas activas, escolarizadas, con coordenadas válidas
        y flags útiles (es_primaria, es_secundaria, es_inicial, es_regular, etc.)
    """
    # 1. Carga adaptativa según extensión
    path_str = str(path).lower()
    if path_str.endswith('.parquet'):
        df = pl.read_parquet(path)
    elif path_str.endswith('.csv'):
        df = pl.read_csv(path, encoding='utf8-lossy', separator=',',
                         truncate_ragged_lines=True)
    elif path_str.endswith(('.xlsx', '.xls')):
        # Polars directo con openpyxl (no requiere pyarrow ni fastexcel).
        # Si openpyxl no está, da mensaje accionable.
        try:
            df = pl.read_excel(path, engine='openpyxl')
        except (ImportError, ModuleNotFoundError) as e:
            raise ImportError(
                "Para leer Excel se necesita openpyxl. Instálalo con:\n"
                "    pip install openpyxl"
            ) from e
    else:
        raise ValueError(f"Extensión no soportada: {path}")

    n_inicial = len(df)
    n_cols_inicial = len(df.columns)

    # 2. Validar columnas esperadas
    faltantes = [c for c in COLS_ESCUELAS if c not in df.columns]
    if faltantes:
        raise ValueError(f"Columnas esperadas no encontradas: {faltantes}")

    # 3. Seleccionar columnas
    df = df.select(COLS_ESCUELAS)

    # 4. Forzar tipos correctos (Excel a veces trae números como string)
    df = df.with_columns([
        pl.col('nlatie').cast(pl.Float64, strict=False),
        pl.col('nlongie').cast(pl.Float64, strict=False),
        pl.col('cod_dist').cast(pl.Int64, strict=False),
    ])

    # 5. Conteos pre-filtro (para diagnóstico transparente)
    diag = {
        'sin_cod_dist':   df['cod_dist'].null_count(),
        'sin_coords':     df.filter(pl.col('nlatie').is_null() |
                                    pl.col('nlongie').is_null()).height,
        'sin_nivmod':     df['nivmod_val'].null_count(),
        'inactivo':       df.filter(pl.col('esta_val') != 'Activo').height,
        'no_escolariz':   df.filter(pl.col('form_valor') != 'Escolarizado').height,
        'coords_fuera':   df.filter(
                              pl.col('nlatie').is_not_null() &
                              pl.col('nlongie').is_not_null() &
                              (~pl.col('nlatie').is_between(LAT_PERU[0], LAT_PERU[1]) |
                               ~pl.col('nlongie').is_between(LON_PERU[0], LON_PERU[1]))
                          ).height,
    }

    # 6. Filtros: descarta y reporta (sin asserts duros)
    df = df.filter(
        pl.col('cod_dist').is_not_null() &
        pl.col('nlatie').is_not_null() &
        pl.col('nlongie').is_not_null() &
        pl.col('nivmod_val').is_not_null() &
        (pl.col('esta_val') == 'Activo') &
        (pl.col('form_valor') == 'Escolarizado') &
        pl.col('nlatie').is_between(LAT_PERU[0], LAT_PERU[1]) &
        pl.col('nlongie').is_between(LON_PERU[0], LON_PERU[1])
    )

    # 7. Renombrar coordenadas a 'lat' / 'lon' (consistencia con otros datasets)
    df = df.rename({'nlatie': 'lat', 'nlongie': 'lon'})

    # 8. Agregar flags vectorizadas
    df = df.with_columns([
        pl.col('nivmod_val').str.contains('Primaria').alias('es_primaria'),
        pl.col('nivmod_val').str.contains('Secundaria').alias('es_secundaria'),
        pl.col('nivmod_val').str.contains('Inicial').alias('es_inicial'),
        pl.col('nivmod_val').is_in(NIVELES_REGULARES).alias('es_regular'),
        pl.col('gesdep_val').is_in(['Sector Educación',
                                     'Convenio con Sector Educación']).alias('es_publico'),
        (pl.col('areaval') == 'Rural').alias('area_rural'),
    ])

    if verbose:
        print(f"[escuelas] inicial:                  {n_inicial:>6}  ({n_cols_inicial} cols)")
        print(f"[escuelas] descartados por:")
        print(f"  sin cod_dist:                      {diag['sin_cod_dist']:>6}")
        print(f"  sin coordenadas:                   {diag['sin_coords']:>6}")
        print(f"  sin nivel modular:                 {diag['sin_nivmod']:>6}")
        print(f"  estado != Activo:                  {diag['inactivo']:>6}")
        print(f"  formalidad != Escolarizado:        {diag['no_escolariz']:>6}")
        print(f"  coordenadas fuera de Perú:         {diag['coords_fuera']:>6}")
        print(f"[escuelas] tras filtros:             {len(df):>6}  "
              f"({len(df)*100/n_inicial:.1f}%, {len(df.columns)} cols)")
        print(f"[escuelas] distritos cubiertos:      {df['cod_dist'].n_unique():>6} / 1,874")
        print()
        print(f"[escuelas] por nivel:")
        print(f"  primaria:    {df['es_primaria'].sum():>6}")
        print(f"  secundaria:  {df['es_secundaria'].sum():>6}")
        print(f"  inicial:     {df['es_inicial'].sum():>6}")
        print(f"  regulares:   {df['es_regular'].sum():>6}")
        print(f"[escuelas] área rural: {df['area_rural'].sum():>6} "
              f"({100*df['area_rural'].sum()/len(df):.1f}%)")
        print(f"[escuelas] públicas:   {df['es_publico'].sum():>6} "
              f"({100*df['es_publico'].sum()/len(df):.1f}%)")

    return df


# ============================================================================
# AGREGACIÓN POR DISTRITO
# ============================================================================

def features_escuelas_por_distrito(df_esc, verbose=True):
    """
    Agrega métricas de escuelas a nivel distrital.

    Features generadas por cod_dist:
      n_escuelas              total de IIEE activas escolarizadas
      n_primarias             primarias (cualquier modalidad)
      n_secundarias           secundarias (cualquier modalidad)
      n_iniciales             iniciales
      n_escuelas_regulares    solo EBR
      n_escuelas_publicas     gestión pública
      n_escuelas_rurales      en zona rural
      tiene_secundaria        bool
      tiene_primaria          bool
      pct_rural_escuelas      % de escuelas en zona rural

    NOTA: km_colegio y km_secundaria se calculan APARTE con KDTree
          una vez que tengas los centroides distritales.

    Args:
        df_esc: output de limpiar_escuelas() (Polars DataFrame)
    Returns:
        pl.DataFrame con un distrito por fila y las métricas agregadas
    """
    agg = df_esc.group_by('cod_dist').agg([
        pl.len().alias('n_escuelas'),
        pl.col('es_primaria').sum().alias('n_primarias'),
        pl.col('es_secundaria').sum().alias('n_secundarias'),
        pl.col('es_inicial').sum().alias('n_iniciales'),
        pl.col('es_regular').sum().alias('n_escuelas_regulares'),
        pl.col('es_publico').sum().alias('n_escuelas_publicas'),
        pl.col('area_rural').sum().alias('n_escuelas_rurales'),
    ]).with_columns([
        (pl.col('n_secundarias') > 0).alias('tiene_secundaria'),
        (pl.col('n_primarias') > 0).alias('tiene_primaria'),
        (100 * pl.col('n_escuelas_rurales') / pl.col('n_escuelas'))
            .round(2).alias('pct_rural_escuelas'),
    ])

    if verbose:
        print(f"[agg_escuelas] distritos con escuelas: {len(agg):>5}")
        print(f"[agg_escuelas] distritos sin secund.:  "
              f"{(~agg['tiene_secundaria']).sum():>5}")
        print(f"[agg_escuelas] distritos sin primaria: "
              f"{(~agg['tiene_primaria']).sum():>5}")

    return agg


# ============================================================================
# UNIÓN CON DATAFRAME DISTRITAL (interop pandas)
# ============================================================================

def merge_escuelas_con_distrital(df_distrital_pd, df_esc_agg):
    """
    Hace el LEFT JOIN del aggregate de escuelas al dataframe distrital.

    Maneja la conversión Polars -> pandas para que sea compatible con el
    pipeline pandas del módulo limpieza.py.

    Args:
        df_distrital_pd: pandas DataFrame (output de limpiar_distrital)
        df_esc_agg:      polars DataFrame (output de features_escuelas_por_distrito)
    Returns:
        pandas DataFrame con las features de escuelas agregadas
    """
    import pandas as pd
    df_esc_pd = df_esc_agg.to_pandas()
    out = df_distrital_pd.merge(df_esc_pd, on='cod_dist', how='left')

    # Distritos sin escuelas: 0, no NaN
    cols_count = ['n_escuelas', 'n_primarias', 'n_secundarias', 'n_iniciales',
                  'n_escuelas_regulares', 'n_escuelas_publicas', 'n_escuelas_rurales']
    for c in cols_count:
        if c in out.columns:
            out[c] = out[c].fillna(0).astype(int)
    out['tiene_secundaria'] = out['tiene_secundaria'].fillna(False)
    out['tiene_primaria'] = out['tiene_primaria'].fillna(False)
    out['pct_rural_escuelas'] = out['pct_rural_escuelas'].fillna(0)

    return out


# ============================================================================
# MAIN — validación contra la muestra
# ============================================================================

if __name__ == '__main__':
    print("=" * 70)
    print("LIMPIEZA DE ESCUELAS — GeoTón Perú 2026 (Polars)")
    print("=" * 70)

    # Test con la muestra (cuando llegue el completo, solo cambias la ruta)
    PATH_MUESTRA = '/mnt/user-data/uploads/escuelas_muestra_100.parquet'
    df_esc = limpiar_escuelas(PATH_MUESTRA)

    print()
    df_agg = features_escuelas_por_distrito(df_esc)

    print(f"\n--- MUESTRA del agregado distrital ---")
    print(df_agg.head(5))
