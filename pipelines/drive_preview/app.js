// Development-only explorer. Files are never synthesized or executed.
export function cleanPath(value) {
  if (typeof value !== "string" || value.startsWith("/") || value.includes("\\") || /[\u0000-\u001f]/u.test(value)) throw new Error("Invalid relative file path");
  const parts = value ? value.split("/") : [];
  if (parts.some(part => !part || part === "." || part === "..")) throw new Error("Invalid relative file path");
  return parts.join("/");
}
export function fileURL(path) {
  return "/files/" + cleanPath(path).split("/").map(encodeURIComponent).join("/");
}
export function isHidden(entry) {
  return Boolean(entry.hidden) || entry.path.split("/").some(part => part.toUpperCase() === "BACKUP" || part.startsWith("."));
}
export function fileType(entry) {
  if (entry.kind === "directory") return {name: "Folder", type: "folder", icon: "folder"};
  const ext = entry.name.split(".").pop().toLowerCase();
  if (ext === "pdf") return {name: "PDF document", type: "pdf", icon: "file"};
  if (ext === "mp4") return {name: "MP4 video", type: "video", icon: "play"};
  if (["txt", "md", "yaml", "yml", "json", "csv", "sha256", "log"].includes(ext)) return {name: "Text document", type: "text", icon: "file"};
  return {name: ext === "apk" ? "Android app · APK" : ext.toUpperCase() + " file", type: "binary", icon: "file"};
}
export function formatBytes(bytes) {
  if (!Number.isSafeInteger(bytes) || bytes < 0) return "Size unavailable";
  if (bytes < 1000) return `${bytes} B`;
  const unit = Math.min(Math.floor(Math.log10(bytes) / 3), 3);
  return `${new Intl.NumberFormat("en", {maximumFractionDigits: 1}).format(bytes / 1000 ** unit)} ${["B", "KB", "MB", "GB"][unit]}`;
}
export function indexFiles(files) {
  if (!Array.isArray(files)) throw new Error("The server did not provide a file inventory");
  const entries = new Map();
  for (const raw of files) {
    const path = cleanPath(raw.path);
    if (!path) continue;
    if (!["directory", "file"].includes(raw.kind)) throw new Error(`Unknown entry kind: ${raw.kind}`);
    const kind = raw.kind;
    if (entries.has(path)) throw new Error(`Duplicate inventory path: ${path}`);
    entries.set(path, {...raw, path, name: path.split("/").pop(), kind});
  }
  for (const entry of [...entries.values()]) {
    const parts = entry.path.split("/");
    parts.pop();
    while (parts.length) {
      const path = parts.join("/");
      if (entries.has(path) && entries.get(path).kind !== "directory") throw new Error(`File conflicts with parent folder: ${path}`);
      if (!entries.has(path)) entries.set(path, {path, name: parts.at(-1), kind: "directory", hidden: false});
      parts.pop();
    }
  }
  for (const entry of entries.values()) {
    const parts = entry.path.split("/"); parts.pop();
    while (parts.length) {
      if (entries.get(parts.join("/"))?.hidden) entry.hidden = true;
      parts.pop();
    }
  }
  return entries;
}
export function folderEntries(entries, folder, query = "", showHidden = false) {
  const needle = query.normalize("NFKD").toLocaleLowerCase();
  return [...entries.values()].filter(entry => {
    const parent = entry.path.includes("/") ? entry.path.slice(0, entry.path.lastIndexOf("/")) : "";
    return parent === folder && (showHidden || !isHidden(entry)) && entry.name.normalize("NFKD").toLocaleLowerCase().includes(needle);
  }).sort((a, b) => (a.kind !== b.kind ? (a.kind === "directory" ? -1 : 1) : a.name.localeCompare(b.name, "en", {numeric: true})));
}

function start() {
  const $ = id => document.getElementById(id);
  let entries = new Map(), folder = "", manifest = {}, previewToken = 0;
  let textController = null;
  const dialog = $("preview");
  const node = (tag, className, text) => {
    const result = document.createElement(tag);
    if (className) result.className = className;
    if (text !== undefined) result.textContent = text;
    return result;
  };
  function showMessage(text) {
    $("message").textContent = text;
    $("message").hidden = !text;
  }
  function navigate(path) {
    folder = cleanPath(path);
    $("search").value = "";
    history.pushState(null, "", "#" + new URLSearchParams({path: folder}));
    render();
  }
  function render() {
    const visible = folderEntries(entries, folder, $("search").value, $("show-hidden").checked);
    $("files").replaceChildren();
    $("breadcrumbs").replaceChildren();
    const segments = ["", ...folder.split("/").filter(Boolean).map((_, index, parts) => parts.slice(0, index + 1).join("/"))];
    for (const [index, path] of segments.entries()) {
      if (index) $("breadcrumbs").append(node("span", "separator", "›"));
      const crumb = node("button", "crumb", path ? path.split("/").pop() : manifest.label || "Drive");
      if (path === folder) crumb.setAttribute("aria-current", "location");
      crumb.addEventListener("click", () => navigate(path));
      $("breadcrumbs").append(crumb);
    }
    $("folder-name").textContent = folder ? folder.split("/").pop() : "On this drive";
    $("back").disabled = !folder;
    $("item-count").textContent = `${visible.length} ${visible.length === 1 ? "item" : "items"}`;
    let bytes = 0, unknown = false;
    for (const entry of visible) {
      const type = fileType(entry);
      const row = node("button", "file-row");
      const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
      svg.setAttribute("class", `file-icon ${type.type}`);
      svg.setAttribute("aria-hidden", "true");
      const use = document.createElementNS(svg.namespaceURI, "use");
      use.setAttribute("href", `#icon-${type.icon}`);
      svg.append(use);
      const copy = node("span", "file-copy");
      copy.append(node("span", "file-name", entry.name));
      let description = type.name;
      if (entry.kind === "directory") {
        const count = folderEntries(entries, entry.path, "", $("show-hidden").checked).length;
        description += ` · ${count} ${count === 1 ? "item" : "items"}`;
      } else {
        description += ` · ${formatBytes(entry.size_bytes)}`;
        if (Number.isSafeInteger(entry.size_bytes)) bytes += entry.size_bytes; else unknown = true;
      }
      copy.append(node("span", "file-meta", description));
      row.append(svg, copy, node("span", "row-arrow", "›"));
      row.addEventListener("click", () => entry.kind === "directory" ? navigate(entry.path) : openFile(entry));
      const li = node("li"); li.append(row); $("files").append(li);
    }
    $("folder-summary").textContent = `${formatBytes(bytes)} in visible files${unknown ? " + unknown sizes" : ""}`;
    showMessage(visible.length ? "" : $("search").value ? "No matching files in this folder." : "This folder has no visible files.");
  }
  function closeFile() {
    previewToken++;
    textController?.abort(); textController = null;
    const video = $("preview-content").querySelector("video");
    if (video) { video.pause(); video.removeAttribute("src"); video.load(); }
    $("preview-content").replaceChildren();
    if (dialog.open) dialog.close();
  }
  async function openFile(entry) {
    closeFile();
    const token = previewToken;
    const type = fileType(entry), url = fileURL(entry.path);
    $("preview-title").textContent = entry.name;
    $("preview-type").textContent = type.name;
    const exactSize = Number.isSafeInteger(entry.size_bytes) ? ` (${entry.size_bytes.toLocaleString("en")} bytes)` : "";
    $("preview-meta").textContent = `${formatBytes(entry.size_bytes)}${exactSize} · ${entry.path}`;
    $("download").href = url; $("download").download = entry.name;
    $("open-native").href = url;
    $("open-native").hidden = type.type === "binary";
    dialog.showModal();
    if (type.type === "pdf") {
      const iframe = node("iframe"); iframe.title = entry.name; iframe.src = url;
      $("preview-content").append(iframe);
    } else if (type.type === "video") {
      const video = node("video"); video.controls = true; video.preload = "metadata"; video.playsInline = true; video.src = url;
      video.append(node("p", null, "Use Open in browser or Download file if this browser cannot play the video."));
      $("preview-content").append(video);
    } else if (type.type === "text") {
      const pre = node("pre", null, "Loading text…"); $("preview-content").append(pre);
      if (entry.size_bytes > 1_000_000) { pre.textContent = "This text file is too large for the inline preview. Download it to open locally."; return; }
      textController = new AbortController();
      try {
        const response = await fetch(url, {signal: textController.signal});
        if (!response.ok) throw new Error(`File request failed (${response.status})`);
        const reader = response.body.getReader(), chunks = [];
        let length = 0;
        for (;;) {
          const {done, value} = await reader.read(); if (done) break;
          length += value.length;
          if (length > 1_000_000) { await reader.cancel(); throw new Error("Text exceeds the inline preview limit. Download it to open locally."); }
          chunks.push(value);
        }
        const data = new Uint8Array(length); let offset = 0;
        for (const chunk of chunks) { data.set(chunk, offset); offset += chunk.length; }
        if (token === previewToken) pre.textContent = new TextDecoder().decode(data);
      } catch (error) { if (token === previewToken && error.name !== "AbortError") pre.textContent = error.message; }
    } else {
      $("preview-content").append(node("p", "binary-info", "This file has no browser preview. Download it to use it with a compatible app or device. Programs and Android apps are never started by this explorer."));
    }
  }
  async function refresh() {
    $("refresh").disabled = true;
    closeFile();
    showMessage("Reading file inventory…");
    try {
      const response = await fetch("/api/drive", {cache: "no-store"});
      if (!response.ok) throw new Error(`Drive inventory request failed (${response.status})`);
      manifest = await response.json(); entries = indexFiles(manifest.files);
      $("drive-label").textContent = manifest.label || "Common Knowledge";
      $("drive-meta").textContent = [manifest.variant != null ? `Variant ${manifest.variant}` : null, manifest.profile ? `${manifest.profile} profile` : null, manifest.source ? `Source ${manifest.source}` : null].filter(Boolean).join(" · ") || "Local file inventory";
      const notice = [manifest.status, ...(Array.isArray(manifest.warnings) ? manifest.warnings : [])].filter(Boolean).join(" · ");
      $("drive-notice").textContent = notice; $("drive-notice").hidden = !notice;
      if (folder && (entries.get(folder)?.kind !== "directory" || (!$("show-hidden").checked && isHidden(entries.get(folder))))) folder = "";
      render();
    } catch (error) {
      $("files").replaceChildren(); $("drive-label").textContent = "Drive unavailable";
      $("drive-meta").textContent = "Refresh after the local server is ready";
      showMessage(error.message);
    } finally { $("refresh").disabled = false; }
  }
  function followLocation() {
    try { folder = cleanPath(new URLSearchParams(location.hash.slice(1)).get("path") || ""); }
    catch { folder = ""; }
    $("search").value = "";
    if (folder && entries.size && entries.get(folder)?.kind !== "directory") folder = "";
    if (!$("show-hidden").checked && folder && isHidden({path: folder, hidden: entries.get(folder)?.hidden})) folder = "";
    if (entries.size) render();
  }
  $("search").addEventListener("input", render);
  $("show-hidden").addEventListener("change", () => {
    if (!$("show-hidden").checked && folder.split("/").some(part => part.toUpperCase() === "BACKUP" || part.startsWith("."))) navigate("");
    else render();
  });
  $("back").addEventListener("click", () => navigate(folder.includes("/") ? folder.slice(0, folder.lastIndexOf("/")) : ""));
  $("viewport").addEventListener("change", event => { document.documentElement.style.setProperty("--preview-width", event.target.value === "fluid" ? "1100px" : `${event.target.value}px`); });
  $("refresh").addEventListener("click", refresh);
  $("close-preview").addEventListener("click", closeFile);
  dialog.addEventListener("cancel", event => { event.preventDefault(); closeFile(); });
  window.addEventListener("popstate", followLocation);
  window.addEventListener("hashchange", followLocation);
  followLocation(); refresh();
}
if (typeof document !== "undefined") start();
