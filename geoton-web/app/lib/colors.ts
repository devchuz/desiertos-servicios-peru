import type { Clasificacion, IntervencionTipo } from "./types";

/**
 * Quita acentos y pasa a MAYÚSCULAS — útil para join robusto contra GeoJSON IDEP.
 */
export function normalizeText(value: unknown): string {
  return String(value ?? "")
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "")
    .trim()
    .toUpperCase();
}

/**
 * Mapea una cadena cualquiera (lower/upper, con o sin tildes, en español o inglés)
 * a una de las 3 clasificaciones canónicas del semáforo.
 */
export function normalizeClasificacion(value?: string): Clasificacion {
  const clean = String(value ?? "")
    .trim()
    .toLowerCase()
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "");

  if (clean.includes("desierto") || clean.includes("rojo")) {
    return "Desierto de servicios";
  }

  if (
    clean.includes("moderado") ||
    clean.includes("amarillo") ||
    clean.includes("privacion")
  ) {
    return "Privación moderada";
  }

  return "Conectado";
}

/**
 * Regla del corte Alkire–Foster (k=4):
 *  0–3 privaciones  → Conectado
 *  4–6 privaciones  → Privación moderada
 *  7–10 privaciones → Desierto de servicios
 */
export function clasificacionFromPrivaciones(n: number): Clasificacion {
  if (!Number.isFinite(n) || n < 4) return "Conectado";
  if (n >= 7) return "Desierto de servicios";
  return "Privación moderada";
}

/**
 * Reduce el texto libre de "intervencion_recomendada" a uno de los tipos
 * canónicos para colorear el mapa por tipo de inversión.
 */
export function normalizeIntervencionTipo(value?: string): IntervencionTipo {
  const clean = String(value ?? "")
    .trim()
    .toLowerCase()
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "");

  if (clean.includes("saneamiento") || clean.includes("alcantarill") || clean.includes("agua")) {
    return "Saneamiento";
  }

  if (clean.includes("tambo") || clean.includes("integral")) {
    return "Tambo / integral";
  }

  if (clean.includes("conectividad") || clean.includes("movil") || clean.includes("internet") || clean.includes("4g")) {
    return "Conectividad";
  }

  if (clean.includes("salud") || clean.includes("educa") || clean.includes("secundaria") || clean.includes("hospital") || clean.includes("colegio")) {
    return "Salud / educación";
  }

  if (clean.includes("reniec") || clean.includes("documento") || clean.includes("dni")) {
    return "RENIEC";
  }

  if (clean.includes("empleo") || clean.includes("trabajo") || clean.includes("pea")) {
    return "Empleo";
  }

  return "Otros";
}

export function normalizeTambo(value: unknown): "Sí" | "No" | "Sin dato" {
  if (value === undefined || value === null || value === "") return "Sin dato";

  const clean = String(value).trim().toLowerCase();

  if (
    clean === "true" ||
    clean === "1" ||
    clean === "si" ||
    clean === "sí" ||
    clean === "✓"
  ) {
    return "Sí";
  }

  if (
    clean === "false" ||
    clean === "0" ||
    clean === "no" ||
    clean === "×" ||
    clean === "-"
  ) {
    return "No";
  }

  return "Sin dato";
}

/**
 * Paleta del semáforo — versión editorial, más sobria que los rojos/verdes neón.
 * Forest / Mustard / Terracotta sobre papel cálido.
 */
export function colorByClasificacion(clasificacion?: string): string {
  if (clasificacion === "Desierto de servicios") return "#A8392B";
  if (clasificacion === "Privación moderada") return "#C99700";
  if (clasificacion === "Conectado") return "#4A7C3C";
  return "#8A8278";
}

export function badgeClassByClasificacion(clasificacion?: string): string {
  if (clasificacion === "Desierto de servicios") return "badge badge-red";
  if (clasificacion === "Privación moderada") return "badge badge-yellow";
  if (clasificacion === "Conectado") return "badge badge-green";
  return "badge badge-gray";
}

/**
 * Colores para vista "por departamento". Se indexa por nombre SIN ACENTOS y EN MAYÚSCULAS
 * (ver normalizeText) para tolerar variantes del CSV INEI.
 *
 * Paleta editorial saturada-pero-sobria, no neón.
 */
export const DEPARTMENT_COLORS: Record<string, string> = {
  AMAZONAS: "#7C9B6A",
  ANCASH: "#8FA5C7",
  APURIMAC: "#B98D5F",
  AREQUIPA: "#C99700",
  AYACUCHO: "#A8392B",
  CAJAMARCA: "#5C8A6B",
  CALLAO: "#1E3A5F",
  CUSCO: "#8B3A62",
  HUANCAVELICA: "#94532E",
  HUANUCO: "#6B8E5A",
  ICA: "#D49B5F",
  JUNIN: "#4A7C3C",
  "LA LIBERTAD": "#B5634A",
  LAMBAYEQUE: "#A0826A",
  LIMA: "#2D4A6B",
  LORETO: "#3D6B5C",
  "MADRE DE DIOS": "#587858",
  MOQUEGUA: "#8C6B4F",
  PASCO: "#806A50",
  PIURA: "#C97B4A",
  PUNO: "#52456E",
  "SAN MARTIN": "#769A5C",
  TACNA: "#8E5F4A",
  TUMBES: "#6FA08A",
  UCAYALI: "#4F7860",
};
