import { coordinates, localSource, mapStyle, validateArchive } from "./model.js";

const settings = JSON.parse(document.querySelector("#settings").textContent);
const status = document.querySelector("#status");
const chooser = document.querySelector("#file");
const controls = document.querySelector("#controls");
const region = document.querySelector("#region");
let map, protocol, selection = 0;
for (const entry of settings.regions) {
  const option = document.createElement("option");
  option.value = entry.id;
  option.textContent = entry.id;
  region.append(option);
}

chooser.addEventListener("change", async () => {
  const file = chooser.files[0];
  if (!file) return;
  const current = ++selection;
  controls.disabled = true;
  if (map) { map.remove(); map = undefined; }
  if (protocol) maplibregl.removeProtocol("pmtiles");
  protocol = undefined;
  status.textContent = "Opening map…";
  try {
    if (file.size !== settings.archive_size_bytes) throw new Error("Choose the supplied map file from this folder.");
    const key = `local-${current}`;
    const archive = new pmtiles.PMTiles(localSource(file, key, pmtiles.FileSource));
    const [header, metadata] = await Promise.all([archive.getHeader(), archive.getMetadata()]);
    if (current !== selection) return;
    validateArchive(header, metadata, settings);
    protocol = new pmtiles.Protocol();
    protocol.add(archive);
    maplibregl.addProtocol("pmtiles", protocol.tile);
    map = new maplibregl.Map({
      container: "map", style: mapStyle(key, header.maxZoom),
      center: [settings.default_view.longitude, settings.default_view.latitude],
      zoom: settings.default_view.zoom, maxZoom: settings.view_max_zoom,
      attributionControl: false, fadeDuration: 0,
      transformRequest: (url) => {
        if (url === `pmtiles://${key}` || url.startsWith(`pmtiles://${key}/`)) return { url };
        throw new Error("This map uses only the selected file.");
      },
    });
    map.addControl(new maplibregl.NavigationControl({ showCompass: true }), "top-right");
    map.on("error", () => { status.textContent = "This map could not be read. Try opening the supplied file again, or use the atlas PDFs."; });
    map.on("load", () => {
      if (current !== selection) return;
      controls.disabled = false;
      status.textContent = `Map ready. Source: ${settings.source_version}. Roads may have changed. This map does not show closures or open services.`;
    });
    map.on("moveend", () => {
      const center = map.getCenter();
      document.querySelector("#position").textContent = `${center.lat.toFixed(5)}, ${center.wrap().lng.toFixed(5)}`;
    });
  } catch (error) {
    if (current === selection) status.textContent = error.message;
  }
});

document.querySelector("#locate").addEventListener("submit", (event) => {
  event.preventDefault();
  try {
    const center = coordinates(document.querySelector("#latitude").value, document.querySelector("#longitude").value);
    region.value = "";
    map.jumpTo({ center, zoom: 12 });
  } catch (error) { status.textContent = error.message; }
});
region.addEventListener("change", () => {
  const entry = settings.regions.find((entry) => entry.id === region.value);
  if (entry) map.fitBounds(entry.bounds, { padding: 32, duration: 0 });
});
document.querySelector("#home").addEventListener("click", () => {
  region.value = "";
  map.jumpTo({ center: [settings.default_view.longitude, settings.default_view.latitude], zoom: settings.default_view.zoom });
});
