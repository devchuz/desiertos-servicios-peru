"""
limpieza.py - Funciones de limpieza para datasets GeoTón Perú 2026

Datasets manejados:
  - SALUD:     instituciones de salud (MINSA + SuSalud)
  - DISTRITAL: indicadores distritales INEI (NBI, servicios, demografía, empleo)

Decisiones de limpieza documentadas:
  SALUD
    - Filtros: est_estado='ACTIVO' AND est_condic='ACTIVO' AND ctg_codigo != '0'
    - 9,254 -> 8,967 establecimientos (96.9% retenidos)
    - 192 hospitales (categoría II-1 a III-E)
    - 15 columnas core + 'es_hospital' flag + lat/lon convertidas

  DISTRITAL
    - 109 -> 53 columnas (drop redundantes _abs, conteos NBI, c5_pX_Y indocumentadas)
    - 1,874 distritos, 0 nulls
    - Renombrado de columnas para evitar la trampa semántica:
        ph_*, phs_*, pv_*, pvs_*   ->   pct_sin_*  (van INVERTIDAS en el original)
        p_lees_si, p_dni, p_af_sis ->   pct_sabe_* / pct_con_*  (positivas)

Uso:
    from limpieza import limpiar_salud, limpiar_distrital, features_salud_por_distrito
    df_sal = limpiar_salud()
    df_dis = limpiar_distrital()
    df_full = features_salud_por_distrito(df_sal, df_dis)
"""

import pandas as pd
import numpy as np


# ============================================================================
# HELPER
# ============================================================================

def _to_float_eu(s):
    """Convierte string con formato europeo (1.234,56) a float.
    Maneja nulos, vacíos y números ya en formato float."""
    if pd.isna(s) or s == '':
        return np.nan
    if isinstance(s, (int, float)):
        return float(s)
    return float(str(s).replace('.', '').replace(',', '.'))


# ============================================================================
# SALUD
# ============================================================================

COLS_SALUD = [
    # Identificadores (6)
    'cod_dist', 'nom_dist', 'cod_dpto', 'nom_dpto', 'cod_prov', 'nom_prov',
    # Características del establecimiento (4)
    'est_nombre', 'clasificac', 'ctg_codigo', 'tipo_estab',
    # Filtros de actividad (2)
    'est_estado', 'est_condic',
    # Coordenadas (2) - se renombran a lat/lon
    'norte_sig', 'este_sig',
    # Bonus: conectividad del propio establecimiento (2)
    'internet', 'conect',
]

# Categorías MINSA que cuentan como "hospital"
HOSP_CATS = ['II-1', 'II-2', 'II-E', 'III-1', 'III-2', 'III-E']


def limpiar_salud(path='/mnt/project/GeoPeruinstituciones_saludPerú_Instituciones_Salud.csv',
                  verbose=True):
    """
    Carga, limpia y filtra instituciones de salud.

    Pasos:
        1. Carga con encoding cp1252 y separador ';'
        2. Selecciona 16 columnas relevantes (de 72)
        3. Convierte coordenadas formato europeo (',' -> '.') a float
        4. Aplica filtros de actividad y categoría
        5. Agrega flag 'es_hospital' (True para categorías II-1 a III-E)

    Returns:
        pd.DataFrame con ~8,967 filas listo para KDTree
    """
    df = pd.read_csv(path, encoding='cp1252', sep=';', low_memory=False)
    n_inicial = len(df)

    # 1. Seleccionar columnas
    df = df[COLS_SALUD].copy()

    # 2. Convertir coordenadas
    df['lat'] = df['norte_sig'].apply(_to_float_eu)
    df['lon'] = df['este_sig'].apply(_to_float_eu)
    df = df.drop(columns=['norte_sig', 'este_sig'])

    # 3. Filtros
    n_activo_estado = (df['est_estado'] == 'ACTIVO').sum()
    n_activo_condic = (df['est_condic'] == 'ACTIVO').sum()
    n_cat_valida = (df['ctg_codigo'] != '0').sum()

    mask = ((df['est_estado'] == 'ACTIVO') &
            (df['est_condic'] == 'ACTIVO') &
            (df['ctg_codigo'] != '0'))
    df = df[mask].reset_index(drop=True)

    # 4. Flag hospital
    df['es_hospital'] = df['ctg_codigo'].isin(HOSP_CATS)

    # 5. Validaciones
    assert df['lat'].between(-19, 0).all(), "Hay latitudes fuera de Perú"
    assert df['lon'].between(-82, -68).all(), "Hay longitudes fuera de Perú"
    assert df['cod_dist'].notna().all(), "Hay cod_dist nulos"

    if verbose:
        print(f"[salud] inicial:               {n_inicial:>5}")
        print(f"[salud]   est_estado=ACTIVO:   {n_activo_estado:>5}")
        print(f"[salud]   est_condic=ACTIVO:   {n_activo_condic:>5}")
        print(f"[salud]   ctg_codigo != '0':   {n_cat_valida:>5}")
        print(f"[salud] tras filtros (AND):    {len(df):>5}  ({len(df)*100/n_inicial:.1f}%)")
        print(f"[salud] hospitales (II-1+):    {df['es_hospital'].sum():>5}")
        print(f"[salud] distritos con estab.:  {df['cod_dist'].nunique():>5} / 1,874")

    return df


# ============================================================================
# DISTRITAL
# ============================================================================

# 42 columnas a mantener (de 109)
# Recorte v2: eliminadas 11 más por error de dato, redundancia y baja varianza
# (ver auditoría: pct_sin_cocina inválida, correlaciones >0.97, discapacidad
# de baja varianza, columnas redundantes matemáticamente)
COLS_DISTRITAL_KEEP = [
    # Identificadores (6)
    'cod_dpto', 'nom_dpto', 'cod_prov', 'nom_prov', 'cod_dist', 'nom_dist',
    # Bases poblacionales y de superficie (3)
    'total_pers', 'num_hog', 'sup_tot',
    # Target NBI y dimensiones (6) — usar en Alkire-Foster, NO en ML (leakage)
    'almenosu_1',                                                # TARGET (pct_nbi)
    'nbi1_porc', 'nbi2_porc', 'nbi3_porc', 'nbi4_porc', 'nbi5_porc',
    # Servicios de vivienda - todas son % SIN (5)
    # ELIMINADO: ph_cocin (pct_sin_cocina) — valores inválidos >100% en 308 distritos
    'pvs_agua_r', 'pvs_sh', 'pvs_aelec', 'pv_ptierra', 'pv_1hab',
    # Servicios de hogar - todas son % SIN (4)
    'ph_lenna', 'phs_pclptb', 'phs_tcelu', 'phs_inter',
    # Demografía: sexo (1) + edad (5)
    # ELIMINADO: p_sex_m (pct_mujeres) — r=1.000 con pct_hombres
    # ELIMINADO: p_pet (pct_pet) — r=0.998 con pct_0a14
    'p_sex_h',
    'p_ge_0a14', 'p_ge_15a29', 'p_ge_30a44', 'p_ge_45a64', 'p_ge_65ym',
    # Quintiles socioeconómicos (5) — no suman 100%, son cortes nacionales
    'pgr_quin1', 'pgr_quin2', 'pgr_quin3', 'pgr_quin4', 'pgr_quin5',
    # Salud - afiliación (2)
    'p_af_sis', 'p_af_ning',
    # Documentación (1)
    # ELIMINADO: p_dni (pct_con_dni) — alta correlación con pct_sin_documento
    'p_no_docum',
    # Educación - alfabetismo (1)
    # ELIMINADO: p_lees_si (pct_sabe_leer) — r=0.98 con pct_no_sabe_leer
    'p_lees_no',
    # Empleo (3)
    # ELIMINADO: p_pea (pct_pea) = pct_pea_ocupada + pct_pea_desocupada (matemáticamente redundante)
    'p_pea_o', 'p_pea_d', 'p_pei',
    # ELIMINADAS: 4 columnas de discapacidad (p_dl_*) — baja varianza, no son
    #   núcleo del problema "desierto de servicios". Recuperar si SHAP las marca.
    # ELIMINADA: c5nbi_porc (pct_hogares_5nbi) — casi constante (media 0.02%, std 0.11)
]

# Renombrado para evitar la trampa semántica
# CRÍTICO: columnas originales ph_, phs_, pv_, pvs_ son % SIN servicio
RENAME_DISTRITAL = {
    # Target
    'almenosu_1':  'pct_nbi',
    # Servicios (% SIN)
    'pvs_agua_r':  'pct_sin_agua',
    'pvs_sh':      'pct_sin_saneamiento',
    'pvs_aelec':   'pct_sin_luz',
    'pv_ptierra':  'pct_piso_tierra',
    'pv_1hab':     'pct_1_habitacion',
    'ph_lenna':    'pct_cocina_lenna',
    'phs_pclptb':  'pct_sin_pc',
    'phs_tcelu':   'pct_sin_celular',
    'phs_inter':   'pct_sin_internet',
    # Demografía (sin pct_mujeres ni pct_pet, eliminados por redundancia)
    'p_sex_h':     'pct_hombres',
    'p_ge_0a14':   'pct_0a14',
    'p_ge_15a29':  'pct_15a29',
    'p_ge_30a44':  'pct_30a44',
    'p_ge_45a64':  'pct_45a64',
    'p_ge_65ym':   'pct_65ymas',
    # Quintiles
    'pgr_quin1':   'pct_quintil1',
    'pgr_quin2':   'pct_quintil2',
    'pgr_quin3':   'pct_quintil3',
    'pgr_quin4':   'pct_quintil4',
    'pgr_quin5':   'pct_quintil5',
    # Salud
    'p_af_sis':    'pct_con_sis',
    'p_af_ning':   'pct_sin_seguro',
    # Documentación (sin pct_con_dni — redundante con pct_sin_documento)
    'p_no_docum':  'pct_sin_documento',
    # Educación (sin pct_sabe_leer — r=0.98 con pct_no_sabe_leer)
    'p_lees_no':   'pct_no_sabe_leer',
    # Empleo (sin pct_pea ni pct_pet)
    'p_pea_o':     'pct_pea_ocupada',
    'p_pea_d':     'pct_pea_desocupada',
    'p_pei':       'pct_pei',
}


def limpiar_distrital(path='/mnt/project/GeoPeruperu_distritosPerú_Distritos.csv',
                      verbose=True):
    """
    Carga, limpia y renombra el dataset distrital INEI (Censo 2017).

    Pasos:
        1. Carga con encoding cp1252 y separador ';'
        2. Selecciona 53 columnas relevantes (de 109)
        3. Convierte columnas numéricas formato europeo a float
        4. Renombra columnas a nombres semánticos claros (pct_*)

    AVISO SEMÁNTICO IMPORTANTE:
        - Columnas pct_sin_*    -> % SIN el servicio (más alto = más privación)
        - Columnas pct_con_*    -> % CON el atributo (más alto = más cobertura)
        - Columnas pct_sabe_*   -> % SABE/PUEDE (positivo)
        - pct_nbi (=almenosu_1) -> % hogares con al menos 1 NBI (TARGET)

    Returns:
        pd.DataFrame con 1,874 distritos y ~53 columnas con nombres claros.
    """
    df = pd.read_csv(path, encoding='cp1252', sep=';', low_memory=False)
    n_inicial = len(df)
    n_cols_inicial = len(df.columns)

    # 1. Validar que las columnas esperadas existan
    faltantes = [c for c in COLS_DISTRITAL_KEEP if c not in df.columns]
    if faltantes:
        raise ValueError(f"Columnas esperadas no encontradas: {faltantes}")

    # 2. Seleccionar columnas
    df = df[COLS_DISTRITAL_KEEP].copy()

    # 3. Convertir numéricos de formato europeo (todas menos los IDs)
    # NOTA: aplicamos sin filtrar por dtype porque pandas reciente puede
    # devolver dtype 'string' (Arrow) en vez de 'object'. _to_float_eu
    # es idempotente para floats ya convertidos.
    cols_id = ['cod_dpto', 'nom_dpto', 'cod_prov', 'nom_prov', 'cod_dist', 'nom_dist']
    cols_num = [c for c in COLS_DISTRITAL_KEEP if c not in cols_id]
    for c in cols_num:
        df[c] = df[c].apply(_to_float_eu)

    # 4. Renombrar
    df = df.rename(columns=RENAME_DISTRITAL)

    # 5. Validaciones
    assert len(df) == 1874, f"Esperaban 1874 distritos, hay {len(df)}"
    assert df['cod_dist'].is_unique, "Hay cod_dist duplicados"
    assert df['pct_nbi'].between(0, 100).all(), "pct_nbi fuera de [0,100]"
    assert df['pct_sin_internet'].between(0, 100).all(), "pct_sin_internet fuera de [0,100]"

    if verbose:
        print(f"[distrital] cargado:           {n_inicial:>5} distritos × {n_cols_inicial} cols")
        print(f"[distrital] tras corte:        {len(df):>5} distritos × {len(df.columns)} cols")
        print(f"[distrital] cod_dist únicos:   {df['cod_dist'].nunique():>5}")
        print(f"[distrital] nulos totales:     {df.isna().sum().sum():>5}")
        print(f"[distrital] media pct_nbi:     {df['pct_nbi'].mean():>5.1f}%")
        print(f"[distrital] media pct_sin_int: {df['pct_sin_internet'].mean():>5.1f}%")

    return df


# ============================================================================
# JOIN: features de salud agregadas al distrito
# ============================================================================

def features_salud_por_distrito(df_salud, df_distrital, verbose=True):
    """
    Agrega métricas de salud al nivel distrital para el modelo.

    Features generadas por distrito:
        n_estab_salud       : total establecimientos activos dentro del distrito
        n_hospitales        : hospitales (II-1+) dentro del distrito
        tiene_estab_salud   : bool, si hay al menos un establecimiento
        tiene_hospital      : bool, si hay al menos un hospital propio

    NOTA: km_hospital y km_salud_cercano se calculan APARTE (con KDTree)
          porque requieren los centroides distritales (polígonos IDEP).
          Esta función solo agrega conteos.

    Args:
        df_salud:     output de limpiar_salud()
        df_distrital: output de limpiar_distrital()
    Returns:
        df_distrital + 4 columnas de salud
    """
    g = df_salud.groupby('cod_dist').agg(
        n_estab_salud=('ctg_codigo', 'size'),
        n_hospitales=('es_hospital', 'sum'),
    ).reset_index()

    df = df_distrital.merge(g, on='cod_dist', how='left')

    # Distritos sin establecimientos: 0, no NaN
    df['n_estab_salud'] = df['n_estab_salud'].fillna(0).astype(int)
    df['n_hospitales'] = df['n_hospitales'].fillna(0).astype(int)
    df['tiene_estab_salud'] = df['n_estab_salud'] > 0
    df['tiene_hospital'] = df['n_hospitales'] > 0

    if verbose:
        print(f"[join] shape final:                  {df.shape}")
        print(f"[join] distritos sin estab. salud:   {(~df['tiene_estab_salud']).sum():>5}")
        print(f"[join] distritos sin hospital:       {(~df['tiene_hospital']).sum():>5}")
        print(f"[join] distritos con >= 1 hospital:  {df['tiene_hospital'].sum():>5}")

    return df


# ============================================================================
# MAIN — ejecutar como script para validar
# ============================================================================

if __name__ == '__main__':
    print("=" * 70)
    print("LIMPIEZA DE DATOS — GeoTón Perú 2026")
    print("=" * 70)

    print("\n--- SALUD ---")
    df_sal = limpiar_salud()

    print("\n--- DISTRITAL ---")
    df_dis = limpiar_distrital()

    print("\n--- JOIN ---")
    df_full = features_salud_por_distrito(df_sal, df_dis)

    print("\n--- MUESTRA ---")
    cols_demo = ['nom_dpto', 'nom_dist', 'total_pers', 'pct_nbi',
                 'pct_sin_internet', 'n_estab_salud', 'n_hospitales']
    print(df_full.sample(5, random_state=42)[cols_demo].to_string(index=False))
