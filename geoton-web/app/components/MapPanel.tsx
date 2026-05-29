import { useEffect, useMemo, useRef } from "react";
import maplibregl from "maplibre-gl";

import type {
  DistritoFeatureProperties,
  DistritoGeoJSON,
  MapMode,
} from "~/lib/types";

import { DEPARTMENT_COLORS } from "~/lib/colors";

type Props = {
  data: DistritoGeoJSON;
  mode: MapMode;
  selectedCodDist?: string | null;
  onSelectDistrict: (props: DistritoFeatureProperties) => void;
};

function escapeHtml(value: unknown) {
  return String(value ?? "—")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function getFillColorExpression(mode: MapMode): maplibregl.ExpressionSpecification {
  // MapLibre acepta estos arrays como expresiones data-driven; en TS armarlas con
  // tipado estricto es ruidoso, por eso usamos `as unknown as` puntualmente.
  if (mode === "departamento") {
    const expression: (string | string[])[] = ["match", ["get", "nom_dpto_norm"]];

    Object.entries(DEPARTMENT_COLORS).forEach(([dpto, color]) => {
      expression.push(dpto, color);
    });

    expression.push("#8A8278"); // fallback warm gray
    return expression as unknown as maplibregl.ExpressionSpecification;
  }

  if (mode === "privaciones") {
    return [
      "interpolate",
      ["linear"],
      ["coalesce", ["to-number", ["get", "n_privaciones"]], 0],
      0,  "#6B9B5C",
      3,  "#A8B85C",
      4,  "#E0B43B",
      6,  "#D08840",
      7,  "#B85A3A",
      10, "#7A2A1F",
    ] as unknown as maplibregl.ExpressionSpecification;
  }

  if (mode === "conectividad") {
    return [
      "interpolate",
      ["linear"],
      ["coalesce", ["to-number", ["get", "pct_sin_internet"]], 0],
      0,   "#E8E4D6",
      40,  "#8FA8B5",
      70,  "#D4A65A",
      90,  "#B8623A",
      100, "#7A2A1F",
    ] as unknown as maplibregl.ExpressionSpecification;
  }

  if (mode === "intervencion") {
    return [
      "match",
      ["get", "intervencion_tipo"],
      "Saneamiento",       "#3B7A8C",
      "Tambo / integral",  "#6B4B7A",
      "Conectividad",      "#C97540",
      "Salud / educación", "#4A7C3C",
      "RENIEC",            "#A04572",
      "Empleo",            "#6E6862",
      "Otros",             "#8A8278",
      "#8A8278",
    ] as unknown as maplibregl.ExpressionSpecification;
  }

  // Semáforo (default) — paleta editorial: forest / mustard / terracotta
  return [
    "match",
    ["get", "clasificacion_norm"],
    "Conectado",             "#4A7C3C",
    "Privación moderada",    "#C99700",
    "Desierto de servicios", "#A8392B",
    "#8A8278",
  ] as unknown as maplibregl.ExpressionSpecification;
}

export default function MapPanel({
  data,
  mode,
  selectedCodDist,
  onSelectDistrict,
}: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const popupRef = useRef<maplibregl.Popup | null>(null);

  const baseStyle = useMemo<maplibregl.StyleSpecification>(
    () => ({
      version: 8,
      sources: {
        carto: {
          type: "raster",
          tiles: [
            "https://basemaps.cartocdn.com/rastertiles/voyager_nolabels/{z}/{x}/{y}.png",
          ],
          tileSize: 256,
          attribution: "© OpenStreetMap contributors © CARTO",
        },
      },
      layers: [
        {
          id: "carto",
          type: "raster",
          source: "carto",
        },
      ],
    }),
    []
  );

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    const map = new maplibregl.Map({
      container: containerRef.current,
      style: baseStyle,
      center: [-75.0, -9.2],
      zoom: 4.6,
      minZoom: 4,
      maxZoom: 11,
    });

    mapRef.current = map;

    map.addControl(new maplibregl.NavigationControl(), "top-right");

    popupRef.current = new maplibregl.Popup({
      closeButton: false,
      closeOnClick: false,
      offset: 12,
    });

    map.on("load", () => {
      map.addSource("distritos", {
        type: "geojson",
        data,
      });

      map.addLayer({
        id: "distritos-fill",
        type: "fill",
        source: "distritos",
        paint: {
          "fill-color": getFillColorExpression(mode),
          "fill-opacity": 0.82,
        },
      });

      map.addLayer({
        id: "distritos-line",
        type: "line",
        source: "distritos",
        paint: {
          "line-color": "#1A1816",
          "line-width": 0.25,
          "line-opacity": 0.35,
        },
      });

      map.addLayer({
        id: "selected-district-line",
        type: "line",
        source: "distritos",
        filter: ["==", ["get", "cod_dist"], selectedCodDist ?? ""],
        paint: {
          "line-color": "#1A1816",
          "line-width": 2.5,
          "line-opacity": 1,
        },
      });

      map.on("click", "distritos-fill", (event) => {
        const feature = event.features?.[0];

        if (!feature?.properties) return;

        onSelectDistrict(feature.properties as DistritoFeatureProperties);
      });

      map.on("mousemove", "distritos-fill", (event) => {
        const feature = event.features?.[0];
        if (!feature?.properties || !popupRef.current) return;

        const p = feature.properties as DistritoFeatureProperties;

        const html = `
          <div class="map-popup">
            <strong>${escapeHtml(p.nom_dist ?? p.nom_dist_ig)}</strong><br/>
            <span>${escapeHtml(p.nom_dpto ?? p.nom_dpto_ig)}</span><br/>
            <hr/>
            <b>Clasificación:</b> ${escapeHtml(p.clasificacion_norm)}<br/>
            <b>Privaciones:</b> ${escapeHtml(p.n_privaciones)}<br/>
            <b>Intervención:</b> ${escapeHtml(
              p.intervencion_recomendada ?? p.intervencion
            )}
          </div>
        `;

        popupRef.current.setLngLat(event.lngLat).setHTML(html).addTo(map);
      });

      map.on("mouseleave", "distritos-fill", () => {
        popupRef.current?.remove();
      });

      map.on("mouseenter", "distritos-fill", () => {
        map.getCanvas().style.cursor = "pointer";
      });

      map.on("mouseleave", "distritos-fill", () => {
        map.getCanvas().style.cursor = "";
      });
    });

    return () => {
      popupRef.current?.remove();
      map.remove();
      mapRef.current = null;
    };
    // Se inicializa una sola vez. Los cambios de data/mode se manejan abajo.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.getSource("distritos")) return;

    const source = map.getSource("distritos") as maplibregl.GeoJSONSource;
    source.setData(data);
  }, [data]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.getLayer("distritos-fill")) return;

    map.setPaintProperty(
      "distritos-fill",
      "fill-color",
      getFillColorExpression(mode)
    );
  }, [mode]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.getLayer("selected-district-line")) return;

    map.setFilter("selected-district-line", [
      "==",
      ["get", "cod_dist"],
      selectedCodDist ?? "",
    ]);
  }, [selectedCodDist]);

  return <div ref={containerRef} className="map-container" />;
}