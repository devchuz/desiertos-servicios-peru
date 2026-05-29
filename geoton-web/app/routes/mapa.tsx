import { useEffect, useMemo, useState } from "react";

import MapLegend from "~/components/MapLegend";
import MapPanel from "~/components/MapPanel";
import DistrictPanel from "~/components/DistrictPanel";

import type {
  DistritoFeatureProperties,
  DistritoGeoJSON,
  MapMode,
} from "~/lib/types";

import {
  clasificacionFromPrivaciones,
  normalizeClasificacion,
  normalizeIntervencionTipo,
  normalizeTambo,
  normalizeText,
} from "~/lib/colors";

function toNumber(value: unknown): number | undefined {
  if (value === undefined || value === null || value === "") return undefined;

  const n = Number(value);
  return Number.isFinite(n) ? n : undefined;
}

function getText(value: unknown, fallback = "") {
  if (value === undefined || value === null) return fallback;
  return String(value);
}

function nf(n: number) {
  return n.toLocaleString("es-PE");
}

function normalizeFeatureProperties(
  props: DistritoFeatureProperties
): DistritoFeatureProperties {
  const nPrivRaw = props.n_privaciones ?? props.privaciones;
  const nPrivaciones = toNumber(nPrivRaw);

  const clasificacionRaw = props.clasificacion ?? props.categoria;

  const clasificacionFinal =
    nPrivaciones !== undefined
      ? clasificacionFromPrivaciones(nPrivaciones)
      : normalizeClasificacion(clasificacionRaw);

  const nombreDpto = props.nom_dpto ?? props.nom_dpto_ig ?? "";
  const nombreDist = props.nom_dist ?? props.nom_dist_ig ?? "";
  const nombreProv = props.nom_prov ?? props.nom_prov_ig ?? "";

  const intervencion =
    props.intervencion_recomendada ?? props.intervencion ?? "Sin recomendación";

  return {
    ...props,
    cod_dist: getText(props.cod_dist).padStart(6, "0"),

    nom_dist: nombreDist,
    nom_dpto: nombreDpto,
    nom_dpto_norm: normalizeText(nombreDpto),
    nom_prov: nombreProv,

    clasificacion_norm: clasificacionFinal,
    clasificacion: clasificacionFinal,

    n_privaciones: nPrivaciones ?? 0,

    total_pers: toNumber(props.total_pers ?? props.poblacion),
    pct_nbi_real: toNumber(props.pct_nbi_real ?? props.pct_nbi),
    pct_nbi_predicho: toNumber(props.pct_nbi_predicho),

    pct_sin_internet: toNumber(props.pct_sin_internet),
    pct_ccpp_con_4g: toNumber(props.pct_ccpp_con_4g),

    km_hospital: toNumber(props.km_hospital),
    km_secundaria: toNumber(props.km_secundaria),

    n_estab_30km: toNumber(props.n_estab_30km),
    n_colegios_30km: toNumber(props.n_colegios_30km),

    impacto: toNumber(props.impacto),

    intervencion_recomendada: intervencion,
    intervencion_tipo: normalizeIntervencionTipo(intervencion),

    tambo_norm: normalizeTambo(props.tiene_tambo),
  };
}

function normalizeGeoJSON(geojson: DistritoGeoJSON): DistritoGeoJSON {
  return {
    ...geojson,
    features: geojson.features.map((feature) => ({
      ...feature,
      properties: normalizeFeatureProperties(feature.properties),
    })),
  };
}

export default function Mapa() {
  const [geojson, setGeojson] = useState<DistritoGeoJSON | null>(null);
  const [selected, setSelected] = useState<DistritoFeatureProperties | null>(
    null
  );

  const [departamento, setDepartamento] = useState("Todos");
  const [clasificacion, setClasificacion] = useState("Todos");
  const [intervencion, setIntervencion] = useState("Todos");
  const [tambo, setTambo] = useState("Todos");
  const [query, setQuery] = useState("");
  const [minPrivaciones, setMinPrivaciones] = useState(0);
  const [mode, setMode] = useState<MapMode>("semaforo");

  useEffect(() => {
    fetch("/data/distritos_simplificado.geojson")
      .then((response) => {
        if (!response.ok) {
          throw new Error("No se pudo cargar distritos_simplificado.geojson");
        }

        return response.json();
      })
      .then((data: DistritoGeoJSON) => {
        const normalized = normalizeGeoJSON(data);
        setGeojson(normalized);
      })
      .catch((error) => {
        console.error(error);
      });
  }, []);

  const departamentos = useMemo(() => {
    if (!geojson) return ["Todos"];

    const values = geojson.features
      .map((f) => f.properties?.nom_dpto)
      .filter(Boolean) as string[];

    return ["Todos", ...Array.from(new Set(values)).sort()];
  }, [geojson]);

  const intervenciones = useMemo(() => {
    if (!geojson) return ["Todos"];

    const values = geojson.features
      .map((f) => f.properties?.intervencion_recomendada)
      .filter(Boolean) as string[];

    return ["Todos", ...Array.from(new Set(values)).sort()];
  }, [geojson]);

  const filteredGeojson = useMemo(() => {
    if (!geojson) return null;

    const q = query.trim().toLowerCase();

    return {
      ...geojson,
      features: geojson.features.filter((feature) => {
        const p = feature.properties;

        const okDpto =
          departamento === "Todos" || p.nom_dpto === departamento;

        const okClas =
          clasificacion === "Todos" ||
          p.clasificacion_norm === clasificacion;

        const okIntervencion =
          intervencion === "Todos" ||
          p.intervencion_recomendada === intervencion;

        const okTambo = tambo === "Todos" || p.tambo_norm === tambo;

        const okPriv = (p.n_privaciones ?? 0) >= minPrivaciones;

        const searchable = `${p.nom_dist ?? ""} ${p.nom_dpto ?? ""} ${
          p.intervencion_recomendada ?? ""
        } ${p.servicios_faltantes ?? ""}`.toLowerCase();

        const okQuery = q === "" || searchable.includes(q);

        return (
          okDpto &&
          okClas &&
          okIntervencion &&
          okTambo &&
          okPriv &&
          okQuery
        );
      }),
    };
  }, [
    geojson,
    departamento,
    clasificacion,
    intervencion,
    tambo,
    minPrivaciones,
    query,
  ]);

  const stats = useMemo(() => {
    if (!filteredGeojson) {
      return {
        total: 0,
        conectados: 0,
        moderados: 0,
        desiertos: 0,
      };
    }

    const features = filteredGeojson.features;

    return {
      total: features.length,
      conectados: features.filter(
        (f) => f.properties?.clasificacion_norm === "Conectado"
      ).length,
      moderados: features.filter(
        (f) => f.properties?.clasificacion_norm === "Privación moderada"
      ).length,
      desiertos: features.filter(
        (f) => f.properties?.clasificacion_norm === "Desierto de servicios"
      ).length,
    };
  }, [filteredGeojson]);

  if (!filteredGeojson) {
    return (
      <div className="card">
        <span className="eyebrow">Cargando</span>
        <h2 style={{ marginTop: 10 }}>Procesando GeoJSON distrital…</h2>
        <p className="muted" style={{ marginTop: 8 }}>
          1 874 polígonos simplificados — listo en un instante.
        </p>
      </div>
    );
  }

  return (
    <>
      <section className="page-header">
        <span className="eyebrow">Explorador territorial · 1 874 distritos</span>
        <h1>
          Mapa del <em>semáforo</em> territorial
        </h1>
        <p className="lede">
          Explora los distritos según clasificación, conectividad, número de
          privaciones, intervención recomendada o departamento. Click sobre
          cualquier polígono para abrir su ficha.
        </p>
      </section>

      <section className="kpi-grid compact">
        <div className="stat">
          <div className="kpi-label">Distritos filtrados</div>
          <div className="kpi-value">{nf(stats.total)}</div>
        </div>

        <div className="stat is-verde">
          <div className="kpi-label">Conectados</div>
          <div className="kpi-value">{nf(stats.conectados)}</div>
        </div>

        <div className="stat is-amarillo">
          <div className="kpi-label">Moderados</div>
          <div className="kpi-value">{nf(stats.moderados)}</div>
        </div>

        <div className="stat is-rojo">
          <div className="kpi-label">Desiertos</div>
          <div className="kpi-value">{nf(stats.desiertos)}</div>
        </div>
      </section>

      <section className="layout-map">
        <div>
          <div className="filters filters-grid">
            <div>
              <label className="field-label">Modo de mapa</label>
              <select
                value={mode}
                onChange={(event) => setMode(event.target.value as MapMode)}
              >
                <option value="semaforo">Semáforo territorial</option>
                <option value="privaciones">Número de privaciones</option>
                <option value="conectividad">% sin internet</option>
                <option value="intervencion">Intervención recomendada</option>
                <option value="departamento">Departamento</option>
              </select>
            </div>

            <div>
              <label className="field-label">Departamento</label>
              <select
                value={departamento}
                onChange={(event) => setDepartamento(event.target.value)}
              >
                {departamentos.map((d) => (
                  <option key={d} value={d}>
                    {d}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="field-label">Clasificación</label>
              <select
                value={clasificacion}
                onChange={(event) => setClasificacion(event.target.value)}
              >
                <option value="Todos">Todos</option>
                <option value="Conectado">Conectado</option>
                <option value="Privación moderada">Privación moderada</option>
                <option value="Desierto de servicios">
                  Desierto de servicios
                </option>
              </select>
            </div>

            <div>
              <label className="field-label">Intervención</label>
              <select
                value={intervencion}
                onChange={(event) => setIntervencion(event.target.value)}
              >
                {intervenciones.map((i) => (
                  <option key={i} value={i}>
                    {i}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="field-label">Tambo PCM</label>
              <select
                value={tambo}
                onChange={(event) => setTambo(event.target.value)}
              >
                <option value="Todos">Todos</option>
                <option value="Sí">Sí tiene Tambo</option>
                <option value="No">No tiene Tambo</option>
                <option value="Sin dato">Sin dato</option>
              </select>
            </div>

            <div>
              <label className="field-label">
                Mínimo de privaciones: {minPrivaciones}
              </label>
              <input
                type="range"
                min={0}
                max={10}
                value={minPrivaciones}
                onChange={(event) =>
                  setMinPrivaciones(Number(event.target.value))
                }
              />
            </div>

            <div className="filter-search">
              <label className="field-label">Buscar</label>
              <input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Distrito, departamento o servicio..."
              />
            </div>
          </div>

          <div className="map-card">
            <MapPanel
              data={filteredGeojson}
              mode={mode}
              selectedCodDist={selected?.cod_dist}
              onSelectDistrict={setSelected}
            />

            <MapLegend mode={mode} />
          </div>
        </div>

        <DistrictPanel district={selected} />
      </section>
    </>
  );
}