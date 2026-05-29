type Metric = {
  label: string;
  value: string;
  helper: string;
};

type Threshold = {
  dimension: "Salud" | "Educación" | "Conectividad" | "Servicios básicos" | "Empleo / identidad";
  indicator: string;
  threshold: string;
  description: string;
  tone: "health" | "education" | "connectivity" | "services" | "employment";
};

type MethodStep = {
  number: string;
  title: string;
  description: string;
};

const metrics: Metric[] = [
  {
    label: "Modelo final",
    value: "XGBoost",
    helper: "Gradient boosting con árboles superficiales",
  },
  {
    label: "R² 5-fold CV",
    value: "0.66",
    helper: "66% de la varianza de NBI explicada por variables territoriales",
  },
  {
    label: "RMSE",
    value: "10.5",
    helper: "Puntos porcentuales de error promedio sobre NBI",
  },
  {
    label: "Features",
    value: "73",
    helper: "Territoriales · servicios · educación · demografía",
  },
];

const thresholds: Threshold[] = [
  {
    dimension: "Salud",
    indicator: "km_hospital",
    threshold: "> 80 km",
    tone: "health",
    description:
      "Más allá de este rango el acceso hospitalario se vuelve crítico para distritos aislados.",
  },
  {
    dimension: "Salud",
    indicator: "pct_sin_seguro",
    threshold: "> 40%",
    tone: "health",
    description:
      "Alta proporción de población sin afiliación a SIS u otro seguro de salud.",
  },
  {
    dimension: "Educación",
    indicator: "km_secundaria",
    threshold: "> 15 km",
    tone: "education",
    description:
      "Distancia crítica a secundaria, relevante en zonas rurales donde la oferta secundaria es más escasa que la primaria.",
  },
  {
    dimension: "Educación",
    indicator: "pct_no_sabe_leer",
    threshold: "> 12%",
    tone: "education",
    description:
      "Nivel elevado de población no alfabetizada, asociado a menor capital humano territorial.",
  },
  {
    dimension: "Conectividad",
    indicator: "pct_sin_internet",
    threshold: "> 90%",
    tone: "connectivity",
    description:
      "Brecha digital casi total: telemedicina, trámites y educación a distancia se vuelven inviables.",
  },
  {
    dimension: "Conectividad",
    indicator: "pct_ccpp_con_4g",
    threshold: "< 40%",
    tone: "connectivity",
    description:
      "Menos de cuatro de cada diez centros poblados cuentan con cobertura móvil 4G real.",
  },
  {
    dimension: "Servicios básicos",
    indicator: "pct_sin_agua",
    threshold: "> 30%",
    tone: "services",
    description:
      "Proporción importante de hogares sin acceso seguro a agua por red pública.",
  },
  {
    dimension: "Servicios básicos",
    indicator: "pct_sin_saneamiento",
    threshold: "> 40%",
    tone: "services",
    description:
      "Variable recurrente como factor dominante en la lista de distritos priorizados.",
  },
  {
    dimension: "Empleo / identidad",
    indicator: "pct_pea_desocupada",
    threshold: "> 6%",
    tone: "employment",
    description:
      "Tasa de desocupación local relativamente alta frente al resto de distritos.",
  },
  {
    dimension: "Empleo / identidad",
    indicator: "pct_sin_documento",
    threshold: "> 5%",
    tone: "employment",
    description:
      "Población indocumentada, lo que afecta acceso a SIS, programas sociales, votación y trámites estatales.",
  },
];

const methodSteps: MethodStep[] = [
  {
    number: "01",
    title: "Validación empírica",
    description:
      "SHAP permite verificar qué variables realmente empujan la predicción de NBI hacia arriba. Esto evita seleccionar indicadores solo por intuición.",
  },
  {
    number: "02",
    title: "Umbrales interpretables",
    description:
      "Los cortes se definen observando puntos de quiebre en los dependence plots. Así, cada privación binaria tiene respaldo en el comportamiento del modelo.",
  },
  {
    number: "03",
    title: "Índice transparente",
    description:
      "Una vez calibrados los umbrales, el índice Alkire-Foster convierte los resultados en un conteo claro de privaciones por distrito.",
  },
];

export default function Modelo() {
  return (
    <main className="model-page">
      {/* HERO simple: sin tarjeta azul, usa .model-hero-simple del CSS */}
      <section className="model-hero-simple">
        <div className="model-hero-copy">
          <span className="eyebrow">Validación predictiva e interpretable</span>

          <h1>
            XGBoost predice la pobreza territorial. <em>SHAP</em> explica el
            porqué.
          </h1>

          <p>
            El modelo no reemplaza al índice: lo calibra. Cada umbral del
            Alkire-Foster nace del punto de inflexión observado en los
            dependence plots, no de un valor arbitrario.
          </p>

          <p className="model-technical-summary">
            <strong>Modelo final:</strong> XGBoost Regressor ·{" "}
            <strong>Target:</strong> pct_nbi continuo, 0-100 ·{" "}
            <strong>Validación:</strong> K-Fold k=5 · <strong>R² CV:</strong>{" "}
            0.66 · <strong>RMSE:</strong> 10.5 · <strong>Variables:</strong> 73
            features territoriales, de servicios, educación y demografía.
          </p>
        </div>
      </section>

      {/* KPIs */}
      <section className="model-kpi-grid" aria-label="Métricas del modelo">
        {metrics.map((metric) => (
          <article className="model-kpi-card" key={metric.label}>
            <span>{metric.label}</span>
            <strong>{metric.value}</strong>
            <p>{metric.helper}</p>
          </article>
        ))}
      </section>

      {/* Por qué dos modelos */}
      <section className="model-section model-section-split">
        <div>
          <span className="eyebrow">Por qué dos modelos y no uno</span>
          <h2>
            ML para <em>validar</em>; Alkire-Foster para <em>comunicar</em>.
          </h2>
        </div>

        <div className="model-prose">
          <p>
            Un modelo XGBoost puede predecir NBI con buen desempeño, pero no es
            directamente trasladable a una recomendación de política pública. El
            jurado y los tomadores de decisión necesitan indicadores binarios,
            umbrales claros y conteos interpretables.
          </p>

          <p>
            Por eso el ML se usa como una herramienta de validación empírica:
            identifica qué variables territoriales pesan realmente en la pobreza
            distrital, descarta variables redundantes y ayuda a ubicar los
            puntos donde cada variable cambia de régimen.
          </p>

          <p>
            El resultado es un índice transparente y auditable, pero calibrado
            con evidencia: los cortes no salen de promedios o números redondos,
            sino del comportamiento observado en el modelo.
          </p>
        </div>
      </section>

      {/* SHAP global */}
      <section className="model-section">
        <div className="model-section-header">
          <div>
            <span className="eyebrow">SHAP global</span>
            <h2>Ranking de variables</h2>
            <p>
              Esta vista permite identificar qué variables tienen mayor
              influencia global sobre la predicción de NBI.
            </p>
          </div>
        </div>

        <figure className="model-figure">
          <div className="plot-frame plot-frame-summary">
            <img
              src="/images/shap_summary.png"
              alt="SHAP summary plot"
              className="plot-image"
              loading="lazy"
            />
          </div>

          <figcaption>
            <strong>Lectura.</strong> Cada punto representa un distrito. El eje X
            muestra el efecto sobre la predicción de NBI y el color representa el
            valor de la variable. Servicios básicos, habitabilidad, ruralidad y
            conectividad aparecen entre los factores más influyentes.
          </figcaption>

          <div className="figure-actions">
            <a
              href="/images/shap_summary.png"
              target="_blank"
              rel="noreferrer"
              className="btn btn-secondary small"
            >
              Abrir imagen completa
            </a>
          </div>
        </figure>
      </section>

      {/* Dependence plots */}
      <section className="model-section">
        <div className="model-section-header">
          <div>
            <span className="eyebrow">Dependence plots</span>
            <h2>De dónde salen los umbrales</h2>
            <p>
              Los puntos de quiebre ayudan a transformar patrones del modelo en
              reglas simples para el índice.
            </p>
          </div>
        </div>

        <figure className="model-figure">
          <div className="plot-frame plot-frame-dependence">
            <img
              src="/images/shap_dependence.png"
              alt="SHAP dependence plots"
              className="plot-image"
              loading="lazy"
            />
          </div>

          <figcaption>
            <strong>Lectura.</strong> El eje X muestra el valor real de la
            variable y el eje Y su efecto SHAP. El punto donde la curva se
            quiebra o cambia de pendiente se usa como umbral empírico.
          </figcaption>

          <div className="figure-actions">
            <a
              href="/images/shap_dependence.png"
              target="_blank"
              rel="noreferrer"
              className="btn btn-secondary small"
            >
              Abrir imagen completa
            </a>
          </div>
        </figure>
      </section>

      {/* Tabla de umbrales */}
      <section className="model-section">
        <div className="model-section-header">
          <div>
            <span className="eyebrow">Umbrales inferidos</span>
            <h2>Variables que alimentan el índice</h2>
            <p>
              Cada umbral resume un punto de cambio observado en SHAP y se
              traduce en una privación binaria dentro del índice Alkire-Foster.
            </p>
          </div>
        </div>

        <div className="model-table-wrap">
          <table className="table model-table">
            <thead>
              <tr>
                <th>Dimensión</th>
                <th>Indicador</th>
                <th>Umbral SHAP</th>
                <th>Interpretación</th>
              </tr>
            </thead>

            <tbody>
              {thresholds.map((item) => (
                <tr key={`${item.dimension}-${item.indicator}`}>
                  <td>
                    <span className={`dimension-pill dim-${item.tone}`}>
                      {item.dimension}
                    </span>
                  </td>
                  <td className="model-code">{item.indicator}</td>
                  <td className="model-threshold">{item.threshold}</td>
                  <td>{item.description}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

    </main>
  );
}