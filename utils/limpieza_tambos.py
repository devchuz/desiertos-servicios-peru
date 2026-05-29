"""
limpieza_tambos.py — Plataformas TAMBOS de la PCM (I Trimestre 2026)

Los Tambos son plataformas de servicios del Estado en zonas rurales remotas
(programa de la Presidencia del Consejo de Ministros). Cada Tambo atiende
varios centros poblados de su "ámbito de influencia".

Importancia para el proyecto:
    Solo 407 de los 1,874 distritos (~22%) tienen Tambo. Cruzar la lista
    de "desiertos de servicios" con la ausencia de Tambo permite recomendar
    al organizador (PCM) dónde poner el siguiente.

Datos: 521 plataformas, I Trimestre 2026
"""

import pandas as pd
import numpy as np


# ============================================================================
# CONFIG
# ============================================================================

COLS_TAMBOS = [
    # Identificadores
    'CODIGO_PLATAFORMA',
    'UBIGEO_CCPP_TAMBO',
    'UBIGEO_DISTRITAL',        # JOIN KEY con cod_dist
    # Geografía
    'DEPARTAMENTO', 'PROVINCIA', 'DISTRITO',
    'CENTRO_POBLADO',
    'TAMBO',                    # nombre del Tambo
    'LATITUD', 'LONGITUD',
    # Métricas de ámbito de influencia
    'CCPP_AMBITO_INFLUENCIA',
    'POBLACION_AMBITO_INFLUENCIA',
    'VIVIENDAS_AMBITO_INFLUENCIA',
    # Operación
    'FECHA_INICIO_SERVICIOS',
]

RENAME_TAMBOS = {
    'CODIGO_PLATAFORMA':             'cod_plataforma',
    'UBIGEO_CCPP_TAMBO':             'cod_ccpp',
    'UBIGEO_DISTRITAL':              'cod_dist',
    'DEPARTAMENTO':                  'nom_dpto',
    'PROVINCIA':                     'nom_prov',
    'DISTRITO':                      'nom_dist',
    'CENTRO_POBLADO':                'centro_poblado',
    'TAMBO':                         'nom_tambo',
    'LATITUD':                       'lat',
    'LONGITUD':                      'lon',
    'CCPP_AMBITO_INFLUENCIA':        'n_ccpp_influencia',
    'POBLACION_AMBITO_INFLUENCIA':   'pob_influencia',
    'VIVIENDAS_AMBITO_INFLUENCIA':   'viv_influencia',
    'FECHA_INICIO_SERVICIOS':        'fecha_inicio',
}

LAT_PERU = (-18.5, 0.0)
LON_PERU = (-82.0, -68.0)


# ============================================================================
# LIMPIEZA
# ============================================================================

def limpiar_tambos(path='/mnt/project/Plataformas_fijas_TAMBOS_prestando_servicios_I_TRIMESTRE_2026.xlsx',
                   verbose=True):
    """
    Carga y limpia el padrón de Plataformas Tambo (PCM).

    Returns:
        pd.DataFrame con 521 Tambos limpios, 14 columnas
    """
    df = pd.read_excel(path)
    n_inicial = len(df)
    n_cols_inicial = len(df.columns)

    # Validar columnas
    faltantes = [c for c in COLS_TAMBOS if c not in df.columns]
    if faltantes:
        raise ValueError(f"Columnas faltantes en Tambos: {faltantes}")

    # Seleccionar y renombrar
    df = df[COLS_TAMBOS].copy()
    df = df.rename(columns=RENAME_TAMBOS)

    # Validar coordenadas
    assert df['lat'].between(LAT_PERU[0], LAT_PERU[1]).all(), \
        "Latitudes fuera de rango Perú"
    assert df['lon'].between(LON_PERU[0], LON_PERU[1]).all(), \
        "Longitudes fuera de rango Perú"
    assert df['cod_dist'].notna().all(), "cod_dist con nulls"

    if verbose:
        print(f"[tambos] inicial:                   {n_inicial:>4}  ({n_cols_inicial} cols)")
        print(f"[tambos] tras corte:                {len(df):>4}  ({len(df.columns)} cols)")
        print(f"[tambos] distritos con Tambo:       {df['cod_dist'].nunique():>4} / 1,874")
        print(f"[tambos] departamentos:             {df['nom_dpto'].nunique():>4}")
        print(f"[tambos] población total atendida:  {df['pob_influencia'].sum():>10,.0f}")
        print(f"[tambos] viviendas atendidas:       {df['viv_influencia'].sum():>10,.0f}")

    return df


# ============================================================================
# AGREGACIÓN POR DISTRITO
# ============================================================================

def features_tambos_por_distrito(df_tambos, verbose=True):
    """
    Agrega Tambos a nivel distrital.

    Features por distrito:
        n_tambos                cantidad de Tambos en el distrito
        tiene_tambo             bool (clave para el indicador Alkire-Foster)
        pob_atendida_tambos     suma de población atendida por Tambos del distrito
        ccpp_atendidos_tambos   suma de CCPP atendidos por Tambos del distrito
    """
    agg = df_tambos.groupby('cod_dist').agg(
        n_tambos=('cod_plataforma', 'count'),
        pob_atendida_tambos=('pob_influencia', 'sum'),
        ccpp_atendidos_tambos=('n_ccpp_influencia', 'sum'),
    ).reset_index()
    agg['tiene_tambo'] = True

    if verbose:
        print(f"[tambos_agg] distritos con al menos 1 Tambo: {len(agg):>4}")
        print(f"[tambos_agg] distritos SIN Tambo:           "
              f"{1874 - len(agg):>4}  ← oportunidad estatal")
        print(f"[tambos_agg] promedio Tambos por distrito:  {agg['n_tambos'].mean():.2f}")

    return agg


def merge_tambos_con_distrital(df_distrital, df_tambos_agg, verbose=True):
    """
    Left join. Distritos sin Tambo se imputan: n_tambos=0, tiene_tambo=False.
    """
    out = df_distrital.merge(df_tambos_agg, on='cod_dist', how='left')

    out['n_tambos'] = out['n_tambos'].fillna(0).astype(int)
    out['tiene_tambo'] = out['tiene_tambo'].fillna(False)
    out['pob_atendida_tambos'] = out['pob_atendida_tambos'].fillna(0)
    out['ccpp_atendidos_tambos'] = out['ccpp_atendidos_tambos'].fillna(0)

    if verbose:
        print(f"[merge_tambos] shape final:                  {out.shape}")
        print(f"[merge_tambos] distritos con Tambo:          "
              f"{out['tiene_tambo'].sum():>4} "
              f"({100*out['tiene_tambo'].sum()/len(out):.1f}%)")
        print(f"[merge_tambos] distritos SIN Tambo:          "
              f"{(~out['tiene_tambo']).sum():>4} "
              f"({100*(~out['tiene_tambo']).sum()/len(out):.1f}%)")

    return out


if __name__ == '__main__':
    print("=" * 70)
    print("LIMPIEZA TAMBOS — GeoTón Perú 2026")
    print("=" * 70)
    df_t = limpiar_tambos()
    print()
    df_t_agg = features_tambos_por_distrito(df_t)
    print(f"\n--- MUESTRA del agregado distrital ---")
    print(df_t_agg.head(5).to_string(index=False))
