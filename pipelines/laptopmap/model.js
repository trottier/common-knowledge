/** The map style deliberately has no remote glyph, sprite or tile endpoints. */
export function mapStyle(key, maxzoom) {
  return {
    version: 8,
    sources: { basemap: { type: "vector", url: `pmtiles://${key}`, maxzoom } },
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
        minzoom: 10, layout: { "symbol-placement": "line",
          "text-field": ["coalesce", ["get", "name:en"], ["get", "name"]],
          "text-font": ["sans-serif"], "text-size": 14 },
        paint: { "text-color": "#111", "text-halo-color": "#fff", "text-halo-width": 1.5 } },
      { id: "place-names", type: "symbol", source: "basemap", "source-layer": "places",
        layout: { "text-field": ["coalesce", ["get", "name:en"], ["get", "name"]],
          "text-font": ["sans-serif"], "text-size": 18, "text-max-width": 10 },
        paint: { "text-color": "#111", "text-halo-color": "#fff", "text-halo-width": 2 } },
    ],
  };
}

export function coordinates(latitude, longitude) {
  if (latitude.trim() === "" || longitude.trim() === "") throw new Error("Enter both coordinates.");
  const lat = Number(latitude), lon = Number(longitude);
  if (!Number.isFinite(lat) || !Number.isFinite(lon) || Math.abs(lat) > 85 || Math.abs(lon) > 180) {
    throw new Error("Use latitude from −85 to 85 and longitude from −180 to 180.");
  }
  return [lon, lat];
}

export function validateArchive(header, metadata, settings) {
  if (header.tileType !== 1 || metadata.ck_dataset !== settings.dataset_id ||
      metadata.source_date_epoch !== settings.source_date_epoch ||
      metadata.ck_source_version !== settings.source_version ||
      header.maxZoom > settings.max_zoom) {
    throw new Error("Choose the supplied map file from this folder.");
  }
}

export function localSource(file, key, FileSource) {
  const source = new FileSource(file);
  // File names can repeat. Each selection needs a fresh cache key.
  return { getKey: () => key, getBytes: source.getBytes.bind(source) };
}
