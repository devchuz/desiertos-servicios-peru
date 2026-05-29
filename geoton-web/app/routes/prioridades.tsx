import { useEffect, useMemo, useState } from "react";
import { normalizeIntervencionTipo, normalizeTambo } from "~/lib/colors";

type Row = {
  ranking: number;
  cod_dist: string;
  nom_dpto: string;
  nom_prov: string;
  nom_dist: string;
  total_pers: number;
  pct_nbi_real: number;
  pct_nbi_predicho?: number;
  n_privaciones: number;
  clasificacion: string;
  pct_sin_internet: number;
  pct_ccpp_con_4g: number;
  n_estab_salud: number;
  n_hospitales: number;
  tiene_tambo: boolean | string;
  factor_dominante: string;
  intervencion_recomendada: string;
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

function intervBadgeColor(tipo: string): string {
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

export default function Prioridades() {
  const [data, setData] = useState<Row[]>([]);
  const [query, setQuery] = useState("");
  const [tipo, setTipo] = useState("Todos");
  const [tamboFilter, setTamboFilter] = useState("Todos");

  useEffect(() => {
    fetch("/data/lista_priorizada.json")
      .then((r) => r.json())
      .then(setData)
      .catch((error) =>
        console.error("Error cargando lista_priorizada.json:", error)
      );
  }, []);

  const ordered = useMemo(() => {
    return [...data].sort((a, b) => a.ranking - b.ranking);
  }, [data]);

  const tipos = useMemo(() => {
    const tt = new Set<string>();
    ordered.forEach((d) =>
      tt.add(normalizeIntervencionTipo(d.intervencion_recomendada))
    );
    return ["Todos", ...Array.from(tt).sort()];
  }, [ordered]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();

    return ordered.filter((d) => {
      const tipoNorm = normalizeIntervencionTipo(d.intervencion_recomendada);
      const tamboNorm = normalizeTambo(d.tiene_tambo);

      const okTipo = tipo === "Todos" || tipoNorm === tipo;
      const okTambo = tamboFilter === "Todos" || tamboNorm === tamboFilter;

      const text =
        `${d.nom_dist} ${d.nom_dpto} ${d.nom_prov} ${d.intervencion_recomendada} ${d.factor_dominante}`.toLowerCase();
      const okQ = q === "" || text.includes(q);

      return okTipo && okTambo && okQ;
    });
  }, [ordered, query, tipo, tamboFilter]);

  const stats = useMemo(() => {
    const totalPob = ordered.reduce(
      (s, d) => s + (Number(d.total_pers) || 0),
      0
    );

    const interventionCount: Record<string, number> = {};
    ordered.forEach((d) => {
      const t = normalizeIntervencionTipo(d.intervencion_recomendada);
      interventionCount[t] = (interventionCount[t] ?? 0) + 1;
    });

    const tamboCount = ordered.filter(
      (d) => normalizeTambo(d.tiene_tambo) === "Sí"
    ).length;

    return {
      total: ordered.length,
      totalPob,
      interventionCount,
      tamboCount,
    };
  }, [ordered]);

  const interventionEntries = useMemo(() => {
    const entries = Object.entries(stats.interventionCount).sort(
      (a, b) => b[1] - a[1]
    );
    const total = entries.reduce((s, [, v]) => s + v, 0) || 1;
    return entries.map(([k, v]) => ({
      tipo: k,
      n: v,
      pct: (v / total) * 100,
      color: intervBadgeColor(k),
    }));
  }, [stats.interventionCount]);

  return (
    <>
      <section className="page-header">
        <span className="eyebrow">Salida operativa · campo 10 Facilita</span>
        <h1>
          Si tuviera <em>presupuesto</em> mañana, ¿qué distritos atacar primero?
        </h1>
        <p className="lede">
          Lista priorizada de los {ordered.length || "—"} distritos con mayor
          <em className="italic-serif"> impacto poblacional</em> (privaciones × población),
          con factor dominante derivado de SHAP local y tipo de intervención
          recomendada.
        </p>

        <div className="meta-line">
          <span>Ordenamiento: impacto descendente</span>
          <span>Factor dominante: SHAP local</span>
          <span>Tipología: Alkire–Foster</span>
        </div>
      </section>

      {/* KPIs */}
      <div className="kpi-grid">
        <div className="stat">
          <div className="kpi-label">Distritos priorizados</div>
          <div className="kpi-value">{nf(stats.total)}</div>
          <div className="kpi-sub">Clasificados como desierto de servicios</div>
        </div>
        <div className="stat is-rojo">
          <div className="kpi-label">Población beneficiada</div>
          <div className="kpi-value">{nf(stats.totalPob)}</div>
          <div className="kpi-sub">Habitantes alcanzados si se ejecuta la lista</div>
        </div>
        <div className="stat">
          <div className="kpi-label">Con Tambo PCM</div>
          <div className="kpi-value">
            {nf(stats.tamboCount)}
            <span className="kpi-unit">/ {nf(stats.total)}</span>
          </div>
          <div className="kpi-sub">
            {stats.total - stats.tamboCount} sin Tambo — gap potencial PCM
          </div>
        </div>
        <div className="stat">
          <div className="kpi-label">Intervención dominante</div>
          <div className="kpi-value" style={{ fontSize: 28 }}>
            {interventionEntries[0]?.tipo ?? "—"}
          </div>
          <div className="kpi-sub">
            {interventionEntries[0]?.n ?? 0} de {stats.total} distritos
          </div>
        </div>
      </div>

      {/* DISTRIBUCIÓN DE INTERVENCIONES */}
      <span className="eyebrow" style={{ display: "block", marginBottom: 14 }}>
        Distribución por tipo de intervención
      </span>

      <div className="card card-ink" style={{ padding: 24 }}>
        <ul className="list-unstyled">
          {interventionEntries.map((ent) => (
            <li
              key={ent.tipo}
              style={{
                display: "grid",
                gridTemplateColumns: "180px 1fr 80px",
                gap: 16,
                alignItems: "center",
                padding: "10px 0",
                borderBottom: "1px solid var(--rule)",
                fontSize: 13.5,
              }}
            >
              <span style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <span
                  style={{
                    width: 14,
                    height: 14,
                    background: ent.color,
                    border: "1px solid var(--ink)",
                    flexShrink: 0,
                  }}
                />
                <strong style={{ fontWeight: 600 }}>{ent.tipo}</strong>
              </span>

              <span
                style={{
                  height: 14,
                  background: "var(--paper-2)",
                  border: "1px solid var(--rule-strong)",
                  position: "relative",
                }}
              >
                <span
                  style={{
                    display: "block",
                    height: "100%",
                    width: `${ent.pct}%`,
                    background: ent.color,
                    transition: "width 0.4s ease",
                  }}
                />
              </span>

              <span
                style={{
                  fontFamily: "var(--font-mono)",
                  fontSize: 12,
                  textAlign: "right",
                  color: "var(--ink-2)",
                  fontFeatureSettings: "'tnum'",
                }}
              >
                {ent.n} · {ent.pct.toFixed(0)}%
              </span>
            </li>
          ))}
        </ul>
      </div>

      {/* FILTROS */}
      <div className="filters" style={{ marginTop: 32 }}>
        <div className="filters-grid">
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
            <label className="field-label">Tambo PCM</label>
            <select
              value={tamboFilter}
              onChange={(e) => setTamboFilter(e.target.value)}
            >
              <option value="Todos">Todos</option>
              <option value="Sí">Sí tiene Tambo</option>
              <option value="No">No tiene Tambo</option>
              <option value="Sin dato">Sin dato</option>
            </select>
          </div>
          <div className="filter-search">
            <label className="field-label">Buscar distrito / depto / intervención</label>
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Raimondi, Ucayali, saneamiento…"
            />
          </div>
        </div>
      </div>

      {/* TABLA */}
      <span className="eyebrow" style={{ display: "block", marginBottom: 14 }}>
        Lista priorizada — top {filtered.length} de {ordered.length}
      </span>

      <div className="table-wrap">
        <table className="table">
          <thead>
            <tr>
              <th>#</th>
              <th>Distrito</th>
              <th>Depto / Prov</th>
              <th className="num">Pob.</th>
              <th className="num">NBI</th>
              <th className="num">Priv.</th>
              <th>Factor dominante</th>
              <th>Intervención</th>
              <th>Tambo</th>
              <th className="num">Impacto</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((d) => {
              const tipoInt = normalizeIntervencionTipo(d.intervencion_recomendada);
              const tamboN = normalizeTambo(d.tiene_tambo);
              return (
                <tr key={d.cod_dist}>
                  <td className="rank">{d.ranking}</td>
                  <td className="distrito">{d.nom_dist}</td>
                  <td className="dpto">
                    {d.nom_dpto}
                    <br />
                    <span style={{ opacity: 0.7, fontSize: 10 }}>
                      {d.nom_prov}
                    </span>
                  </td>
                  <td className="num">{nf(d.total_pers)}</td>
                  <td className="num">{pf(d.pct_nbi_real, 1)}</td>
                  <td className="num">
                    <strong style={{ color: "var(--rojo)" }}>{d.n_privaciones}</strong>
                    <span style={{ color: "var(--ink-3)" }}>/10</span>
                  </td>
                  <td>
                    <code
                      style={{
                        fontFamily: "var(--font-mono)",
                        fontSize: 11,
                        background: "var(--paper-2)",
                        padding: "2px 6px",
                        color: "var(--ink-2)",
                      }}
                    >
                      {d.factor_dominante}
                    </code>
                  </td>
                  <td>
                    <span
                      className="chip"
                      style={{
                        background: "var(--paper)",
                        borderColor: intervBadgeColor(tipoInt),
                        color: intervBadgeColor(tipoInt),
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
                  <td className="num">
                    <strong>{nf(d.impacto)}</strong>
                  </td>
                </tr>
              );
            })}
            {filtered.length === 0 && (
              <tr>
                <td colSpan={10} style={{ textAlign: "center", padding: 32, color: "var(--ink-3)" }}>
                  Ningún distrito cumple los filtros actuales.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <p
        style={{
          marginTop: 14,
          fontSize: 11.5,
          color: "var(--ink-3)",
          fontFamily: "var(--font-mono)",
          letterSpacing: "0.05em",
        }}
      >
        Impacto = privaciones × población. NBI según INEI Censo 2017,
        proyectada 2022. Factor dominante extraído de SHAP local del modelo
        XGBoost.
      </p>
    </>
  );
}
