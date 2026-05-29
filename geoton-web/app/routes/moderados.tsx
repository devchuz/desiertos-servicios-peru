import { useEffect, useMemo, useState } from "react";
import {
  badgeClassByClasificacion,
  normalizeClasificacion,
  normalizeIntervencionTipo,
  normalizeTambo,
} from "~/lib/colors";

type Row = {
  cod_dist: string;
  nom_dpto: string;
  nom_prov: string;
  nom_dist: string;
  total_pers: number;
  pct_nbi_real: number;
  n_privaciones: number;
  clasificacion: string;
  pct_sin_internet: number;
  pct_ccpp_con_4g: number;
  factor_dominante: string;
  intervencion_recomendada: string;
  tiene_tambo?: boolean | string;
  impacto: number;
};

function nf(n?: number) {
  if (n === undefined || n === null || Number.isNaN(Number(n))) return "—";
  return Number(n).toLocaleString("es-PE");
}

function pf(n?: number, digits = 0) {
  if (n === undefined || n === null || Number.isNaN(Number(n))) return "—";
  return `${Number(n).toFixed(digits)}%`;
}

function intervColor(tipo: string): string {
  switch (tipo) {
    case "Saneamiento":       return "#3B7A8C";
    case "Tambo / integral":  return "#6B4B7A";
    case "Conectividad":      return "#C97540";
    case "Salud / educación": return "#4A7C3C";
    case "RENIEC":            return "#A04572";
    case "Empleo":            return "#6E6862";
    default:                  return "#8A8278";
  }
}

const PAGE_SIZE = 50;

export default function Moderados() {
  const [data, setData] = useState<Row[]>([]);
  const [query, setQuery] = useState("");
  const [dpto, setDpto] = useState("Todos");
  const [tipo, setTipo] = useState("Todos");
  const [privFiltro, setPrivFiltro] = useState<number | "todos">("todos");
  const [shown, setShown] = useState(PAGE_SIZE);

  useEffect(() => {
    fetch("/data/indice_af.json")
      .then((r) => r.json())
      .then(setData);
  }, []);

  const moderados = useMemo<Row[]>(() => {
    return (data || []).filter(
      (d) => normalizeClasificacion(d.clasificacion) === "Privación moderada"
    );
  }, [data]);

  const departamentos = useMemo(() => {
    const set = new Set<string>();
    moderados.forEach((d) => d.nom_dpto && set.add(d.nom_dpto));
    return ["Todos", ...Array.from(set).sort()];
  }, [moderados]);

  const tipos = useMemo(() => {
    const set = new Set<string>();
    moderados.forEach((d) =>
      set.add(normalizeIntervencionTipo(d.intervencion_recomendada))
    );
    return ["Todos", ...Array.from(set).sort()];
  }, [moderados]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();

    return moderados
      .filter((d) => {
        const okDpto = dpto === "Todos" || d.nom_dpto === dpto;
        const okTipo =
          tipo === "Todos" ||
          normalizeIntervencionTipo(d.intervencion_recomendada) === tipo;
        const okPriv = privFiltro === "todos" || d.n_privaciones === privFiltro;
        const text =
          `${d.nom_dist} ${d.nom_dpto} ${d.nom_prov} ${d.intervencion_recomendada} ${d.factor_dominante}`.toLowerCase();
        const okQ = q === "" || text.includes(q);
        return okDpto && okTipo && okPriv && okQ;
      })
      .sort(
        (a, b) =>
          (b.n_privaciones ?? 0) - (a.n_privaciones ?? 0) ||
          (b.impacto ?? 0) - (a.impacto ?? 0)
      );
  }, [moderados, query, dpto, tipo, privFiltro]);

  // Reset paginación cuando cambian filtros
  useEffect(() => {
    setShown(PAGE_SIZE);
  }, [query, dpto, tipo, privFiltro]);

  const visible = filtered.slice(0, shown);

  const stats = useMemo(() => {
    const pob = filtered.reduce((s, d) => s + (Number(d.total_pers) || 0), 0);
    const pobAll = moderados.reduce((s, d) => s + (Number(d.total_pers) || 0), 0);
    const byPriv: Record<number, number> = { 4: 0, 5: 0, 6: 0 };
    moderados.forEach((d) => {
      const p = d.n_privaciones;
      if (p === 4 || p === 5 || p === 6) byPriv[p] += 1;
    });
    return {
      filteredCount: filtered.length,
      totalCount: moderados.length,
      pob,
      pobAll,
      byPriv,
    };
  }, [moderados, filtered]);

  const privBars = useMemo(() => {
    const max = Math.max(
      stats.byPriv[4] || 0,
      stats.byPriv[5] || 0,
      stats.byPriv[6] || 0,
      1
    );
    return [4, 5, 6].map((p) => ({
      n: p,
      count: stats.byPriv[p] || 0,
      pct: ((stats.byPriv[p] || 0) / max) * 100,
    }));
  }, [stats]);

  return (
    <>
      <section className="page-header">
        <span className="eyebrow">Privación moderada · 4 a 6 privaciones</span>
        <h1>
          Los distritos <em>amarillos</em>: aún no son desiertos, pero ya están
          en el filo.
        </h1>
        <p className="lede">
          Acá vive la mayor parte del problema en términos de población. Son
          distritos con brechas <em className="italic-serif">sectoriales</em>{" "}
          — usualmente saneamiento o conectividad — que sin intervención
          oportuna se deslizan a desierto.
        </p>

        <div className="meta-line">
          <span>Corte Alkire–Foster: k = 4</span>
          <span>Ordenamiento: privaciones desc.</span>
          <span>Fuente: índice AF distrital</span>
        </div>
      </section>

      {/* KPIs */}
      <div className="kpi-grid">
        <div className="stat is-amarillo">
          <div className="kpi-label">Distritos moderados</div>
          <div className="kpi-value">{nf(stats.totalCount)}</div>
          <div className="kpi-sub">De los 1 874 del universo nacional</div>
        </div>

        <div className="stat is-amarillo">
          <div className="kpi-label">Población amarilla</div>
          <div className="kpi-value">{nf(stats.pobAll)}</div>
          <div className="kpi-sub">Habitantes en riesgo de caer al rojo</div>
        </div>

        <div className="stat">
          <div className="kpi-label">Distritos filtrados</div>
          <div className="kpi-value">{nf(stats.filteredCount)}</div>
          <div className="kpi-sub">Con los filtros actuales aplicados</div>
        </div>

        <div className="stat">
          <div className="kpi-label">Población filtrada</div>
          <div className="kpi-value">{nf(stats.pob)}</div>
          <div className="kpi-sub">
            {stats.pobAll > 0
              ? `${Math.round((stats.pob / stats.pobAll) * 100)}% del total moderado`
              : ""}
          </div>
        </div>
      </div>

      {/* Distribución por nº de privaciones */}
      <span className="eyebrow" style={{ display: "block", marginBottom: 14 }}>
        Cómo se distribuyen las {nf(stats.totalCount)} privaciones moderadas
      </span>

      <div className="card card-ink" style={{ padding: 24, marginBottom: 36 }}>
        <div style={{ display: "grid", gap: 12 }}>
          {privBars.map((b) => (
            <div
              key={b.n}
              style={{
                display: "grid",
                gridTemplateColumns: "120px 1fr 110px",
                alignItems: "center",
                gap: 16,
              }}
            >
              <div
                style={{
                  fontFamily: "var(--font-display)",
                  fontStyle: "italic",
                  fontSize: 18,
                  letterSpacing: "-0.01em",
                }}
              >
                {b.n} privaciones
              </div>
              <div
                style={{
                  height: 16,
                  background: "var(--paper-2)",
                  border: "1px solid var(--rule-strong)",
                  position: "relative",
                }}
              >
                <span
                  style={{
                    display: "block",
                    height: "100%",
                    width: `${b.pct}%`,
                    background:
                      b.n === 6
                        ? "#D08840"
                        : b.n === 5
                        ? "#D4A23A"
                        : "#E0B43B",
                    transition: "width 0.4s ease",
                  }}
                />
              </div>
              <div
                style={{
                  fontFamily: "var(--font-mono)",
                  fontSize: 12.5,
                  textAlign: "right",
                  color: "var(--ink-2)",
                  fontFeatureSettings: "'tnum'",
                }}
              >
                {nf(b.count)} distritos
              </div>
            </div>
          ))}
        </div>
        <p
          style={{
            marginTop: 16,
            fontSize: 12,
            color: "var(--ink-3)",
            fontStyle: "italic",
            fontFamily: "var(--font-display)",
          }}
        >
          Los distritos con 6 privaciones son los candidatos más inmediatos a
          caer al rojo — vigilancia prioritaria.
        </p>
      </div>

      {/* FILTROS */}
      <div className="filters">
        <div className="filters-grid">
          <div>
            <label className="field-label">Departamento</label>
            <select value={dpto} onChange={(e) => setDpto(e.target.value)}>
              {departamentos.map((d) => (
                <option key={d} value={d}>
                  {d}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="field-label">Tipo de intervención</label>
            <select value={tipo} onChange={(e) => setTipo(e.target.value)}>
              {tipos.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="field-label">N° de privaciones</label>
            <select
              value={privFiltro === "todos" ? "todos" : String(privFiltro)}
              onChange={(e) =>
                setPrivFiltro(
                  e.target.value === "todos" ? "todos" : Number(e.target.value)
                )
              }
            >
              <option value="todos">Todas (4–6)</option>
              <option value="6">6 — borde rojo</option>
              <option value="5">5</option>
              <option value="4">4 — borde verde</option>
            </select>
          </div>
          <div className="filter-search">
            <label className="field-label">
              Buscar distrito, departamento, servicio
            </label>
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Ej. Apurímac, saneamiento, alfabetización…"
            />
          </div>
        </div>
      </div>

      {/* TABLA */}
      <span className="eyebrow" style={{ display: "block", marginBottom: 14 }}>
        Mostrando {nf(visible.length)} de {nf(stats.filteredCount)} distritos
      </span>

      <div className="table-wrap">
        <table className="table">
          <thead>
            <tr>
              <th>Distrito</th>
              <th>Departamento</th>
              <th className="num">Pob.</th>
              <th className="num">Priv.</th>
              <th className="num">NBI</th>
              <th className="num">% sin internet</th>
              <th>Intervención</th>
              <th>Tambo</th>
            </tr>
          </thead>
          <tbody>
            {visible.map((d) => {
              const tipoInt = normalizeIntervencionTipo(d.intervencion_recomendada);
              const tamboN = normalizeTambo(d.tiene_tambo);
              return (
                <tr key={d.cod_dist}>
                  <td className="distrito">{d.nom_dist}</td>
                  <td className="dpto">
                    {d.nom_dpto}
                    <br />
                    <span style={{ opacity: 0.7, fontSize: 10 }}>
                      {d.nom_prov}
                    </span>
                  </td>
                  <td className="num">{nf(d.total_pers)}</td>
                  <td className="num">
                    <strong style={{ color: "#8A6800" }}>
                      {d.n_privaciones}
                    </strong>
                    <span style={{ color: "var(--ink-3)" }}>/10</span>
                  </td>
                  <td className="num">{pf(d.pct_nbi_real, 1)}</td>
                  <td className="num">{pf(d.pct_sin_internet, 0)}</td>
                  <td>
                    <span
                      className="chip"
                      style={{
                        background: "var(--paper)",
                        borderColor: intervColor(tipoInt),
                        color: intervColor(tipoInt),
                      }}
                    >
                      {d.intervencion_recomendada}
                    </span>
                  </td>
                  <td>
                    {tamboN === "Sí" ? (
                      <span className="badge badge-green">Sí</span>
                    ) : tamboN === "No" ? (
                      <span className="badge badge-red">No</span>
                    ) : (
                      <span className="badge badge-gray">s/d</span>
                    )}
                  </td>
                </tr>
              );
            })}

            {visible.length === 0 && (
              <tr>
                <td
                  colSpan={8}
                  style={{
                    textAlign: "center",
                    padding: 32,
                    color: "var(--ink-3)",
                  }}
                >
                  No hay distritos moderados que cumplan los filtros.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Paginación */}
      {visible.length < filtered.length && (
        <div
          style={{
            marginTop: 18,
            display: "flex",
            justifyContent: "center",
          }}
        >
          <button
            onClick={() => setShown((s) => s + PAGE_SIZE)}
            className="btn"
            style={{ background: "var(--paper)", color: "var(--ink)" }}
          >
            Ver {Math.min(PAGE_SIZE, filtered.length - visible.length)} más
          </button>
        </div>
      )}

      <p
        style={{
          marginTop: 22,
          fontSize: 11.5,
          color: "var(--ink-3)",
          fontFamily: "var(--font-mono)",
          letterSpacing: "0.05em",
        }}
      >
        Datos: índice Alkire–Foster sobre 10 indicadores binarios.
        Clasificación moderada = 4 a 6 privaciones. La intervención se infiere
        del factor dominante en el SHAP local del modelo XGBoost.
      </p>
    </>
  );
}
