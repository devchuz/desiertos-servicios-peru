import type { FeatureCollection, Geometry } from "geojson";

export type Clasificacion =
  | "Conectado"
  | "Privación moderada"
  | "Desierto de servicios";

export type MapMode =
  | "semaforo"
  | "privaciones"
  | "conectividad"
  | "intervencion"
  | "departamento";

export type TamboStatus = "Sí" | "No" | "Sin dato";

export type IntervencionTipo =
  | "Saneamiento"
  | "Tambo / integral"
  | "Conectividad"
  | "Salud / educación"
  | "RENIEC"
  | "Empleo"
  | "Otros";

export type DistritoFeatureProperties = {
  cod_dist: string;

  nom_dist?: string;
  nom_dist_ig?: string;

  nom_dpto?: string;
  nom_dpto_ig?: string;
  nom_dpto_norm?: string;

  nom_prov?: string;
  nom_prov_ig?: string;

  clasificacion?: string;
  clasificacion_norm?: Clasificacion;
  categoria?: string;

  n_privaciones?: number;
  privaciones?: number;

  total_pers?: number;
  poblacion?: number;

  pct_nbi_real?: number;
  pct_nbi?: number;
  pct_nbi_predicho?: number;

  pct_sin_internet?: number;
  pct_ccpp_con_4g?: number;

  km_hospital?: number;
  km_secundaria?: number;
  n_estab_30km?: number;
  n_colegios_30km?: number;

  tiene_tambo?: boolean | string | number;
  tambo_norm?: TamboStatus;

  factor_dominante?: string;
  intervencion?: string;
  intervencion_recomendada?: string;
  intervencion_tipo?: IntervencionTipo;

  impacto?: number;

  servicios_faltantes?: string;
  dimensiones_faltantes?: string;
};

export type DistritoGeoJSON = FeatureCollection<
  Geometry,
  DistritoFeatureProperties
>;