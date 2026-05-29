import { index, route, type RouteConfig } from "@react-router/dev/routes";

export default [
  index("./routes/home.tsx"),
  route("mapa", "./routes/mapa.tsx"),
  route("prioridades", "./routes/prioridades.tsx"),
  route("moderados", "./routes/moderados.tsx"),
  route("modelo", "./routes/modelo.tsx"),
] satisfies RouteConfig;