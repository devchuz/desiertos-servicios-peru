import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router";

type Row = {
  cod_dist?: string;
  nom_dist?: string;
  nom_dpto?: string;
  categoria?: string;
  clasificacion?: string;
  privaciones?: number;
  n_privaciones?: number;
  total_pers?: number;
  poblacion?: number;
  pct_nbi?: number;
  pct_nbi_real?: number;
  intervencion?: string;
  intervencion_recomendada?: string;
  tiene_tambo?: boolean | string | number;
};

type Clasificacion =
  | "Conectado"
  | "Privación moderada"
  | "Desierto de servicios";

function toNumber(value: unknown): number {
  const n = Number(value);
  return Number.isFinite(n) ? n : 0;
}

function normalizeText(value: unknown) {
  return String(value ?? "")
    .trim()
    .toLowerCase()
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "");
}

function clasificacionFromPrivaciones(n: number): Clasificacion {
  if (n >= 7) return "Desierto de servicios";
  if (n >= 4) return "Privación moderada";
  return "Conectado";
}

function normalizeClasificacion(row: Row): Clasificacion {
  const privaciones = toNumber(row.n_privaciones ?? row.privaciones);

  if (privaciones > 0 || row.n_privaciones !== undefined || row.privaciones !== undefined) {
    return clasificacionFromPrivaciones(privaciones);
  }

  const raw = normalizeText(row.clasificacion ?? row.categoria);

  if (raw.includes("desierto") || raw.includes("rojo")) {
    return "Desierto de servicios";
  }

  if (
    raw.includes("moderado") ||
    raw.includes("privacion") ||
    raw.includes("amarillo")
  ) {
    return "Privación moderada";
  }

  return "Conectado";
}

function formatNumber(value: number) {
  return value.toLocaleString("es-PE");
}

function formatDecimal(value: number, digits = 3) {
  return value.toFixed(digits);
}

function KpiCard({
  label,
  value,
  helper,
  tone,
}: {
  label: string;
  value: string;
  helper?: string;
  tone?: "green" | "yellow" | "red" | "blue" | "dark";
}) {
  return (
    <div className={`kpi-card ${tone ? `kpi-${tone}` : ""}`}>
      <div className="kpi-card-label">{label}</div>
      <div className="kpi-card-value">{value}</div>
      {helper && <div className="kpi-card-helper">{helper}</div>}
    </div>
  );
}

export default function Home() {
  const [data, setData] = useState<Row[]>([]);

  useEffect(() => {
    fetch("/data/indice_af.json")
      .then((response) => {
        if (!response.ok) {
          throw new Error("No se pudo cargar /data/indice_af.json");
        }

        return response.json();
      })
      .then(setData)
      .catch((error) => {
        console.error("Error cargando datos del índice:", error);
      });
  }, []);

  const stats = useMemo(() => {
    const rows = data.map((row) => {
      const nPrivaciones = toNumber(row.n_privaciones ?? row.privaciones);
      const clasificacion = normalizeClasificacion(row);
      const poblacion = toNumber(row.total_pers ?? row.poblacion);

      return {
        ...row,
        nPrivaciones,
        clasificacion,
        poblacion,
      };
    });

    const total = rows.length;

    const conectados = rows.filter(
      (r) => r.clasificacion === "Conectado"
    ).length;

    const moderados = rows.filter(
      (r) => r.clasificacion === "Privación moderada"
    ).length;

    const desiertos = rows.filter(
      (r) => r.clasificacion === "Desierto de servicios"
    ).length;

    const pobresTerritoriales = rows.filter((r) => r.nPrivaciones >= 4);

    const poblacionAfectada = pobresTerritoriales.reduce(
      (acc, r) => acc + r.poblacion,
      0
    );

    const poblacionDesiertos = rows
      .filter((r) => r.nPrivaciones >= 7)
      .reduce((acc, r) => acc + r.poblacion, 0);

    const H = total > 0 ? pobresTerritoriales.length / total : 0;

    const A =
      pobresTerritoriales.length > 0
        ? pobresTerritoriales.reduce((acc, r) => acc + r.nPrivaciones / 10, 0) /
          pobresTerritoriales.length
        : 0;

    const mpi = H * A;

    const topDptos = Object.entries(
      rows.reduce<Record<string, number>>((acc, row) => {
        if (row.nPrivaciones >= 7) {
          const dpto = row.nom_dpto ?? "Sin dato";
          acc[dpto] = (acc[dpto] ?? 0) + 1;
        }

        return acc;
      }, {})
    )
      .sort((a, b) => b[1] - a[1])
      .slice(0, 5);

    const topPrioritarios = rows
      .filter((r) => r.nPrivaciones >= 7)
      .sort((a, b) => b.nPrivaciones * b.poblacion - a.nPrivaciones * a.poblacion)
      .slice(0, 8);

    return {
      total,
      conectados,
      moderados,
      desiertos,
      poblacionAfectada,
      poblacionDesiertos,
      H,
      A,
      mpi,
      topDptos,
      topPrioritarios,
    };
  }, [data]);

  return (
    <>
      <section className="hero-panel">
        <div className="hero-content">
          <div className="hero-eyebrow">Sistema de priorización territorial</div>

          <h1>Semáforo Territorial GeoTón</h1>

          <p>
            Identifica distritos conectados, distritos con privación moderada y
            desiertos de servicios donde la inversión pública debería priorizarse
            para cerrar brechas de salud, educación, conectividad y servicios
            básicos.
          </p>

          <div className="hero-actions">
            <Link to="/mapa" className="btn btn-primary">
              Ver mapa interactivo
            </Link>

            <Link to="/moderados" className="btn btn-secondary">
              Analizar moderados
            </Link>
          </div>
        </div>

        <div className="hero-summary-card">
          <div className="summary-title">Lectura rápida</div>

          <div className="summary-row">
            <span>Unidad de análisis</span>
            <strong>Distrito</strong>
          </div>

          <div className="summary-row">
            <span>Metodología</span>
            <strong>Alkire-Foster + SHAP</strong>
          </div>

          <div className="summary-row">
            <span>Modelo interpretable</span>
            <strong>XGBoost</strong>
          </div>

          <div className="summary-row">
            <span>Salida operativa</span>
            <strong>Semáforo territorial</strong>
          </div>
        </div>
      </section>

      <section className="kpi-dashboard">
        <KpiCard
          label="Distritos analizados"
          value={formatNumber(stats.total)}
          helper="Cobertura nacional distrital"
          tone="dark"
        />

        <KpiCard
          label="Conectados"
          value={formatNumber(stats.conectados)}
          helper="0–3 privaciones"
          tone="green"
        />

        <KpiCard
          label="Moderados"
          value={formatNumber(stats.moderados)}
          helper="4–6 privaciones"
          tone="yellow"
        />

        <KpiCard
          label="Desiertos"
          value={formatNumber(stats.desiertos)}
          helper="7–10 privaciones"
          tone="red"
        />
      </section>

      <section className="kpi-dashboard secondary">
        <KpiCard
          label="Población afectada"
          value={formatNumber(stats.poblacionAfectada)}
          helper="Personas en distritos con ≥4 privaciones"
          tone="blue"
        />

        <KpiCard
          label="Población en desiertos"
          value={formatNumber(stats.poblacionDesiertos)}
          helper="Máxima urgencia territorial"
          tone="red"
        />

        <KpiCard
          label="H · Incidencia"
          value={formatDecimal(stats.H, 3)}
          helper="% de distritos con pobreza territorial"
        />

        <KpiCard
          label="MPI territorial"
          value={formatDecimal(stats.mpi, 3)}
          helper="H × A"
        />
      </section>

      <section className="dashboard-grid">
        <div className="dashboard-card wide">
          <div className="section-header">
            <div>
              <h2>Qué muestra el sistema</h2>
              <p>
                El semáforo traduce variables territoriales en una lectura de
                decisión pública: dónde intervenir, con qué prioridad y qué tipo
                de servicio falta.
              </p>
            </div>
          </div>

          <div className="method-grid">
            <div className="method-item">
              <div className="method-number">01</div>
              <h3>Medición de brechas</h3>
              <p>
                Se integran indicadores de salud, educación, conectividad,
                servicios básicos y documentación a nivel distrital.
              </p>
            </div>

            <div className="method-item">
              <div className="method-number">02</div>
              <h3>Clasificación territorial</h3>
              <p>
                Cada distrito recibe un puntaje de 0 a 10 privaciones y se
                clasifica en verde, amarillo o rojo.
              </p>
            </div>

            <div className="method-item">
              <div className="method-number">03</div>
              <h3>Recomendación de acción</h3>
              <p>
                El factor dominante del modelo ayuda a sugerir si priorizar
                saneamiento, conectividad, salud, educación o intervención
                integral.
              </p>
            </div>
          </div>
        </div>

        <div className="dashboard-card">
          <div className="section-header">
            <div>
              <h2>Desiertos por departamento</h2>
              <p>Top departamentos con mayor cantidad de distritos rojos.</p>
            </div>
          </div>

          <div className="ranking-list">
            {stats.topDptos.length > 0 ? (
              stats.topDptos.map(([dpto, count], index) => (
                <div className="ranking-row" key={dpto}>
                  <div className="ranking-index">{index + 1}</div>
                  <div className="ranking-name">{dpto}</div>
                  <div className="ranking-value">{count}</div>
                </div>
              ))
            ) : (
              <p className="muted">Cargando ranking...</p>
            )}
          </div>
        </div>
      </section>

      <section className="dashboard-card">
        <div className="section-header">
          <div>
            <h2>Distritos rojos de mayor impacto</h2>
            <p>
              Priorizados por una lógica simple: número de privaciones ×
              población distrital.
            </p>
          </div>

          <Link to="/mapa" className="btn btn-secondary small">
            Explorar en mapa
          </Link>
        </div>

        <div className="table-wrapper">
          <table className="table">
            <thead>
              <tr>
                <th>#</th>
                <th>Distrito</th>
                <th>Departamento</th>
                <th>Privaciones</th>
                <th>Población</th>
                <th>Intervención</th>
              </tr>
            </thead>

            <tbody>
              {stats.topPrioritarios.map((row, index) => (
                <tr key={`${row.cod_dist}-${index}`}>
                  <td>{index + 1}</td>
                  <td>{row.nom_dist ?? "—"}</td>
                  <td>{row.nom_dpto ?? "—"}</td>
                  <td>{row.nPrivaciones}</td>
                  <td>{formatNumber(row.poblacion)}</td>
                  <td>
                    {row.intervencion_recomendada ??
                      row.intervencion ??
                      "Sin dato"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="dashboard-card">
        <div className="section-header">
          <div>
            <h2>Lámina consolidada</h2>
            <p>
              Vista resumida del mapa, ranking de factores y tabla priorizada.
            </p>
          </div>
        </div>

        <img
          src="/images/lamina_geoton.png"
          alt="Lámina consolidada GeoTón"
          className="full-image"
        />
      </section>
    </>
  );
}