import type { DistritoFeatureProperties } from "~/lib/types";
import { badgeClassByClasificacion } from "~/lib/colors";

type Props = {
  district: DistritoFeatureProperties | null;
};

function formatNumber(value?: number) {
  if (value === undefined || value === null || Number.isNaN(Number(value))) {
    return "—";
  }

  return Number(value).toLocaleString("es-PE");
}

function formatDecimal(value?: number, digits = 1) {
  if (value === undefined || value === null || Number.isNaN(Number(value))) {
    return "—";
  }

  return Number(value).toFixed(digits);
}

function formatPercent(value?: number) {
  if (value === undefined || value === null || Number.isNaN(Number(value))) {
    return "—";
  }

  return `${Number(value).toFixed(1)}%`;
}

function splitList(value?: string) {
  if (!value || value.trim() === "" || value.trim() === "—") return [];

  return value
    .split(",")
    .map((x) => x.trim())
    .filter(Boolean);
}

function MetricItem({
  label,
  value,
}: {
  label: string;
  value: string | number;
}) {
  return (
    <div className="metric-item">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

export default function DistrictPanel({ district }: Props) {
  if (!district) {
    return (
      <div className="card panel district-panel">
        <h2>Selecciona un distrito</h2>
        <p className="muted">
          Haz click sobre un distrito del mapa para ver su diagnóstico,
          conectividad, servicios faltantes e intervención recomendada.
        </p>
      </div>
    );
  }

  const nombreDistrito =
    district.nom_dist ?? district.nom_dist_ig ?? "Distrito sin nombre";

  const nombreDpto =
    district.nom_dpto ?? district.nom_dpto_ig ?? "Departamento sin dato";

  const clasificacion = district.clasificacion_norm ?? "Conectado";

  const servicios = splitList(district.servicios_faltantes);
  const dimensiones = splitList(district.dimensiones_faltantes);

  return (
    <div className="card panel district-panel">
      <div className="district-header">
        <div>
          <h2>{nombreDistrito}</h2>
          <p>{nombreDpto}</p>
        </div>

        <span className={badgeClassByClasificacion(clasificacion)}>
          {clasificacion}
        </span>
      </div>

      <div className="mini-grid">
        <MetricItem
          label="Privaciones"
          value={formatNumber(district.n_privaciones)}
        />

        <MetricItem
          label="Población"
          value={formatNumber(district.total_pers ?? district.poblacion)}
        />

        <MetricItem
          label="NBI real"
          value={formatPercent(district.pct_nbi_real)}
        />

        <MetricItem label="Impacto" value={formatNumber(district.impacto)} />
      </div>

      <section className="panel-section">
        <h3>Conectividad y acceso</h3>

        <MetricItem
          label="% sin internet"
          value={formatPercent(district.pct_sin_internet)}
        />

        <MetricItem
          label="% CCPP con 4G"
          value={formatPercent(district.pct_ccpp_con_4g)}
        />

      </section>

      <section className="panel-section">
        <h3>Servicios faltantes</h3>

        {servicios.length > 0 ? (
          <div className="chip-list">
            {servicios.map((x) => (
              <span key={x} className="chip">
                {x}
              </span>
            ))}
          </div>
        ) : (
          <p className="muted">No registra servicios faltantes críticos.</p>
        )}
      </section>

      <section className="panel-section">
        <h3>Dimensiones afectadas</h3>

        {dimensiones.length > 0 ? (
          <div className="chip-list">
            {dimensiones.map((x) => (
              <span key={x} className="chip chip-blue">
                {x}
              </span>
            ))}
          </div>
        ) : (
          <p className="muted">Sin dimensiones críticas registradas.</p>
        )}
      </section>

      <section className="panel-section">
        <h3>Acción pública sugerida</h3>

        <p>
          <strong>Intervención:</strong>
          <br />
          {district.intervencion_recomendada ??
            district.intervencion ??
            "Sin recomendación disponible"}
        </p>

        <p>
          <strong>Tipo:</strong>
          <br />
          {district.intervencion_tipo ?? "Sin dato"}
        </p>

        <p>
          <strong>Factor dominante:</strong>
          <br />
          {district.factor_dominante ?? "Sin dato"}
        </p>

        <p>
          <strong>Tambo PCM:</strong>{" "}
          <span
            className={
              district.tambo_norm === "No"
                ? "badge badge-red"
                : district.tambo_norm === "Sí"
                ? "badge badge-green"
                : "badge badge-gray"
            }
          >
            {district.tambo_norm ?? "Sin dato"}
          </span>
        </p>
      </section>
    </div>
  );
}