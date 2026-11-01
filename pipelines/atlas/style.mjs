/** Only road, water, boundary and place context; no infrastructure/POI layer. */
export function style(maxzoom) {
  return {
    version: 8,
    glyphs: "ck-font://{fontstack}/{range}.pbf",
    sources: { basemap: { type: "vector", tiles: ["ck-tile://{z}/{x}/{y}"], maxzoom } },
    layers: [
      { id: "paper", type: "background", paint: { "background-color": "#faf9f4" } },
      { id: "water", type: "fill", source: "basemap", "source-layer": "water",
        paint: { "fill-color": "#d6eaf4" } },
      { id: "roads", type: "line", source: "basemap", "source-layer": "roads",
        paint: { "line-color": "#77746c", "line-width": ["interpolate", ["linear"], ["zoom"], 5, 0.5, 14, 2] } },
      { id: "major-roads", type: "line", source: "basemap", "source-layer": "roads",
        filter: ["in", ["get", "kind"], ["literal", ["highway", "major_road"]]],
        paint: { "line-color": "#9f5f18", "line-width": ["interpolate", ["linear"], ["zoom"], 5, 1, 14, 4] } },
      { id: "road-names", type: "symbol", source: "basemap", "source-layer": "roads",
        minzoom: 10, layout: { "symbol-placement": "line", "text-field": ["coalesce", ["get", "name:en"], ["get", "name"]],
          "text-font": ["Noto Sans Regular"], "text-size": 14 },
        paint: { "text-color": "#111111", "text-halo-color": "#ffffff", "text-halo-width": 1.5 } },
      { id: "place-names", type: "symbol", source: "basemap", "source-layer": "places",
        layout: { "text-field": ["coalesce", ["get", "name:en"], ["get", "name"]],
          "text-font": ["Noto Sans Regular"], "text-size": 19, "text-max-width": 10 },
        paint: { "text-color": "#111111", "text-halo-color": "#ffffff", "text-halo-width": 2 } },
    ],
  };
}
