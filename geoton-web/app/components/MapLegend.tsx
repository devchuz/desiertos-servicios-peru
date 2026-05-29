import type { MapMode } from "~/lib/types";
import { DEPARTMENT_COLORS } from "~/lib/colors";

type Props = {
  mode: MapMode;
};

export default function MapLegend({ mode }: Props) {
  if (mode === "departamento") {
    return (
      <div className="map-legend map-legend-scroll">
        <h4>Departamentos</h4>

        {Object.entries(DEPARTMENT_COLORS).map(([dpto, color]) => (
          <div className="legend-row" key={dpto}>
            <span className="legend-dot" style={{ background: color }} />
            {dpto}
          </div>
        ))}
      </div>
    );
  }

  if (mode === "privaciones") {
    return (
      <div className="map-legend">
        <h4>N° de privaciones</h4>
        <div className="legend-gradient privaciones" />
        <div className="legend-scale">
          <span>0</span>
          <span>5</span>
          <span>10</span>
        </div>
      </div>
    );
  }

  if (mode === "conectividad") {
    return (
      <div className="map-legend">
        <h4>% sin internet</h4>
        <div className="legend-gradient conectividad" />
        <div className="legend-scale">
          <span>0%</span>
          <span>50%</span>
          <span>100%</span>
        </div>
      </div>
    );
  }

  if (mode === "intervencion") {
    return (
      <div className="map-legend">
        <h4>Intervención</h4>

        <div className="legend-row">
          <span className="legend-dot" style={{ background: "#0ea5e9" }} />
          Saneamiento
        </div>

        <div className="legend-row">
          <span className="legend-dot" style={{ background: "#8b5cf6" }} />
          Tambo / integral
        </div>

        <div className="legend-row">
          <span className="legend-dot" style={{ background: "#f97316" }} />
          Conectividad
        </div>

        <div className="legend-row">
          <span className="legend-dot" style={{ background: "#22c55e" }} />
          Salud / educación
        </div>

        <div className="legend-row">
          <span className="legend-dot" style={{ background: "#ec4899" }} />
          RENIEC
        </div>

        <div className="legend-row">
          <span className="legend-dot" style={{ background: "#64748b" }} />
          Otros
        </div>
      </div>
    );
  }

  return (
    <div className="map-legend">
      <h4>Semáforo territorial</h4>

      <div className="legend-row">
        <span className="legend-dot" style={{ background: "#22c55e" }} />
        Conectado: 0–3 privaciones
      </div>

      <div className="legend-row">
        <span className="legend-dot" style={{ background: "#facc15" }} />
        Moderado: 4–6 privaciones
      </div>

      <div className="legend-row">
        <span className="legend-dot" style={{ background: "#dc2626" }} />
        Desierto: 7–10 privaciones
      </div>
    </div>
  );
}