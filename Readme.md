# GeoTón Perú 2026 — Desiertos y brechas de servicios

Sistema replicable de **priorización territorial de la inversión pública en el Perú**, presentado a la **Categoría 3 (Territorio Conectado)** del concurso GeoTón Perú 2026 (Secretaría de Gobierno y Transformación Digital — PCM).

Combina seis datasets georreferenciados abiertos de **GEO Perú**, aprendizaje automático interpretable (**XGBoost + SHAP**) y el **índice multidimensional de Alkire-Foster** para clasificar los 1 874 distritos del país en un semáforo territorial (verde / amarillo / rojo) y emitir, para cada distrito, una recomendación de intervención con sector ejecutor responsable.


---

## 1. Resultados principales

| Métrica | Valor |
|---|---|
| Variación de la pobreza (NBI) explicada por factores territoriales | **65,6 %** (R² CV 5-fold, XGBoost) |
| Incidencia de pobreza territorial (H, ≥4 privaciones) | 0,465 |
| Intensidad promedio entre los pobres (A) | 0,472 |
| **MPI territorial** (H × A) | **0,219** |

Clasificación tricolor de los 1 874 distritos:

| Nivel | Privaciones | Distritos | Población | % país |
|---|---|---|---|---|
| 🟢 Conectado | 0–3 | 1 002 | 23 181 892 | 81,1 % |
| 🟡 Moderado | 4–6 | 837 | 5 194 350 | 18,2 % |
| 🔴 Desierto | 7–10 | 35 | 198 095 | 0,7 % |

Hallazgos accionables: **18 de los 35 desiertos (51,4 %) no tienen Tambo PCM**; en el nivel moderado, el **98,4 %** de la población se atiende con solo dos sectores (MVCS-saneamiento y MTC-conectividad).

---

## 2. Estructura del repositorio

```
geoton-peru-2026/
├── 01_consolidado.ipynb        # Limpieza + agregación → tabla maestra distrital
├── 02_modelo.ipynb             # Feature engineering + ML + SHAP
├── 03_alkire_foster.ipynb      # Índice AF + recomendación + mapa + exports
│
├── utils/                      # Módulos reutilizables del pipeline
│   ├── limpieza.py             #   salud (MINSA) + indicadores distritales (INEI)
│   ├── limpieza_escuelas.py    #   padrón MINEDU (Polars)
│   ├── limpieza_osiptel.py     #   cobertura móvil OSIPTEL (doble agregación CCPP→distrito)
│   ├── limpieza_tambos.py      #   plataformas Tambos PCM
│   ├── limpieza_ig.py          #   polígonos distritales INEI/IDEP (swap WKT lat/lon)
│   ├── feature_engineering.py  #   distancias BallTree-Haversine, ratios, interacciones
│   ├── tuning_modelos.py       #   RandomizedSearchCV de 4 modelos de ensamble
│   └── generar_geojson_distritos.py  # exporta GeoJSON+JSON para la app web
│
├── data/                       # CSV/XLSX originales (NO versionados — ver §3)
├── output/                     # Salidas del pipeline (CSV, parquet, lámina PNG)
│
└── geoton-web/                 # App web del semáforo territorial
    ├── app/
    │   ├── root.tsx, routes.ts
    │   ├── routes/             # home, mapa, prioridades, moderados, modelo
    │   ├── components/         # MapPanel, MapLegend, DistrictPanel
    │   └── lib/                # colors.ts, types.ts
    └── public/data/            # distritos_simplificado.geojson, indice_af.json, lista_priorizada.json
```

---

## 3. Datasets (fuentes GEO Perú)

| # | Dataset | Registros | Fuente | Uso |
|---|---|---|---|---|
| 1 | Indicadores distritales (Censo 2017) | 1 874 | INEI | Target NBI + variables socioeconómicas |
| 2 | Establecimientos de salud activos | 9 254 (→8 967) | MINSA | Distancia a hospital/posta más cercana |
| 3 | Padrón de locales educativos | ~80 000 | MINEDU | Distancia a colegio secundario |
| 4 | Cobertura móvil por operador | 51 366 | OSIPTEL | Conectividad digital (4G) por CCPP |
| 5 | Plataformas fijas Tambos | 521 | PCM | Cruce desierto ↔ ausencia de Tambo |
| 6 | Polígonos distritales | 1 874 | INEI/IDEP | Centroides + mapa coroplético |

> Los archivos crudos no se incluyen en el repo por tamaño/licencia. Descargarlos del portal GEO Perú y colocarlos en `data/`. La clave universal de join entre todos los datasets es **`cod_dist`** (ubigeo, 6 dígitos, int64) — **nunca unir por nombre** (hay distritos homónimos, p. ej. varios "SAN ISIDRO").

---

## 4. Metodología (3 bloques)

### Bloque A — Ingeniería de variables territoriales
- **Centroides** distritales a partir de los polígonos INEI/IDEP. Ojo: el WKT viene en orden no estándar `lat lon` (`limpieza_ig.py` hace el swap automático).
- **Distancias** centroide → servicio con **BallTree + métrica Haversine** (no KDTree euclidiano: 1° de longitud en Lima ≠ en Loreto). Genera `km_hospital`, `km_salud_cercano`, `km_colegio`, `km_secundaria`, más densidades `n_estab_30km` / `n_colegios_30km`.
- **Conectividad**: cobertura 4G OSIPTEL agregada CCPP→distrito y `pct_sin_internet` censal.
- **Ratios e interacciones** que no usan el target (p. ej. `indice_aislamiento = km_hospital × pct_sin_internet / 100`).
- ~30 variables territoriales por distrito.

### Bloque B — Aprendizaje supervisado + SHAP
- **Target:** tasa de NBI (`pct_nbi`, continua). Se entrenan 4 modelos (XGBoost, LightGBM, HistGradientBoosting, RandomForest) con RandomizedSearchCV (`n_iter=40`) y CV 5-fold.
- **Modelo final: XGBoost** (R²=0,656; RMSE=10,51) — se fuerza XGBoost por sus contribuciones SHAP nativas vía DMatrix.
- Las **5 NBI individuales se excluyen** de las features (data leakage). Entrenamiento sobre 1 663 distritos con NBI y features completas.
- **SHAP**: summary plot global + dependence plots para derivar los **umbrales empíricos** del índice (punto donde la curva SHAP cruza cero / cambia de régimen).

### Bloque C — Índice Alkire-Foster + recomendación
- **10 indicadores binarios** en 5 dimensiones, con umbrales calibrados por SHAP:

| Dimensión | Indicador | Umbral |
|---|---|---|
| Salud | distancia a hospital | > 50 km |
| Salud | % sin seguro | > 25 % |
| Educación | distancia a secundaria | > 10 km |
| Educación | % que no sabe leer | > 20 % |
| Conectividad | % sin internet | > 80 % |
| Conectividad | % CCPP con 4G | < 50 % |
| Servicios básicos | % sin agua de red | > 40 % |
| Servicios básicos | % sin saneamiento | > 30 % |
| Empleo | % PEA desocupada | > 5 % |
| Documentación | % sin documento | > 10 % |

- Puntaje de privación `s ∈ {0..10}`; cortes **s≥4 (pobreza territorial)** y **s≥7 (desierto)**.
- **Motor de recomendación:** SHAP local descompone la NBI predicha por distrito; la variable con mayor contribución positiva (filtrada para excluir síntomas puros de pobreza) define el factor dominante → intervención + sector ejecutor. Priorización por `impacto = privaciones × población`.
- El índice AF, al ser aritmético, se aplica a los **1 874 distritos completos** (no depende del subconjunto del ML).

---

## 5. Cómo reproducir

### Pipeline (Python)
```bash
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install pandas numpy polars scikit-learn xgboost lightgbm shap \
            geopandas shapely matplotlib openpyxl pyarrow jupyter
```
Colocar los datasets en `data/` y ejecutar en orden:
1. `01_consolidado.ipynb` → tabla maestra distrital limpia.
2. `02_modelo.ipynb` → modelo + SHAP + umbrales.
3. `03_alkire_foster.ipynb` → índice, lista priorizada, mapa, lámina y exports.

**Salidas en `output/`:** `indice_af.csv`, `lista_priorizada.csv`, `metricas_af.csv`, `feature_importance.csv`, `shap_values.parquet`, `lamina_geoton.png`.

### App web (`geoton-web/`)
Visualizador interactivo del semáforo: stack **React Router v7 + MapLibre GL**, con 5 vistas (`home`, `mapa`, `prioridades`, `moderados`, `modelo`) y modos de mapa (semáforo, privaciones, conectividad, intervención, departamento). Consume los JSON/GeoJSON en `public/data/` generados por `utils/generar_geojson_distritos.py`.

> ⚠️ El paquete entregado solo contiene `app/` y `public/`. Para correrlo falta el andamiaje del proyecto (`package.json`, `vite.config.ts`, `tsconfig.json`). Reconstruir con un template de React Router v7 e instalar `react-router`, `maplibre-gl` y `geojson`.

---

## 6. Decisiones de diseño cerradas

- **Nivel distrital, no provincial** (n=1 874 habilita ML predictivo legítimo).
- **Un solo target: NBI.** Estándar INEI, continuo, disponible.
- **Alkire-Foster + SHAP son complementarios, no competidores:** el índice es aritmética transparente; el ML calibra los umbrales.
- **Umbrales derivados del SHAP**, no por juicio experto — esta es la contribución metodológica central.
- **Lista cerrada de 6 datasets.** Se excluyen deliberadamente red vial MTC, comisarías, satelital y brechas CEPLAN (fuera del núcleo o ya son índices de terceros). Quedan como trabajo futuro.
- **Trampa semántica:** columnas `ph_*/phs_*/pv_*/pvs_*` vienen invertidas (% SIN el servicio) → renombradas a `pct_sin_*`. Formato europeo de números (`3.312,37`) convertido a float.
- **OSIPTEL:** los 211 distritos sin reporte se imputan a 0 % (la ausencia de reporte ES la señal).
- **Anclas de validación:** Lima Cercado / San Isidro (menor privación) ↔ distritos de Condorcanqui (mayor). Auditoría completa del dataset antes de codificar.

---

## 7. Revisión — puntos a verificar antes de entregar

Detectados al consolidar este README; ninguno bloquea la entrega, pero conviene resolverlos para coherencia del expediente:

1. **Texto "CatBoost" obsoleto.** El `print` del resumen Facilita en `03_alkire_foster.ipynb` dice *"umbrales calibrados con SHAP sobre CatBoost"*, pero el modelo final es **XGBoost** (Notebook 2 e informe PDF). Corregir la cadena.
2. **Conteo desactualizado en el mismo `print`.** Dice *"850 distritos con ≥4 privaciones"*; el `indice_af.json` final y el PDF dan **872** (837 moderado + 35 desierto). El JSON publicado es el correcto — actualizar el texto del print.
3. **App web incompleta.** El zip no incluye `package.json` ni config de build; documentado en §5.
4. **Coherencia de cifras informe ↔ exports.** Confirmar que `metricas_af.csv` reporte H=0,465 / A=0,472 / MPI=0,219 (los del PDF) y no valores de una corrida intermedia.
5. **Haversine en línea recta** subestima el aislamiento real en Amazonía (transporte fluvial) y Andes (trochas) — ya está declarado como limitación en el informe; mantenerlo visible.

---

## 8. Articulación institucional

Sin nueva legislación ni nuevas unidades ejecutoras. Aprovecha instrumentos existentes: **PCM-SGTD** (gobernanza del índice), **MVCS** (saneamiento), **MTC** (conectividad), **MINSA** (salud), **MINEDU** (secundarias), **RENIEC** (documentación) y **MEF** vía FONIPREL e INVIERTE.PE para focalización presupuestal.

## 9. Referencias clave
Alkire & Foster (2011); UNDP/OPHI Global MPI (2023); Bhatt et al. (Medellín, 2023); Zheng et al. (Fujian, 2024); Hamzaoui et al. (Taounate, 2022); Chen & Guestrin (XGBoost, 2016); Lundberg & Lee (SHAP, 2017); Kain (1968); Geurs & van Wee (2004).