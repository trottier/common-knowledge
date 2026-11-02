# Development Drive Explorer

These assets are served by the local development server, never copied to a
production drive. They browse the actual selected file inventory. Viewport
presets are generic widths, not physical-phone acceptance evidence.

From the repository, run:

```sh
rtk proxy uv run ck explore --drive /path/to/assembled-drive
```

Open `http://127.0.0.1:8766/`. This command only reads the selected folder;
it neither builds missing content nor validates an image. Keep any partial
development tree clearly identified as incomplete. The server binds to this
computer's loopback interface. Use `--port` to change its port.

Serve `index.html` at `/`, and `app.css` and `app.js` at `/static/`.
`GET /api/drive` returns `label`, `variant`, `profile`, `root`, and a `files`
array. Each entry has a relative POSIX `path`, `name`, `kind` (`directory` or
`file`), actual `size_bytes` for files, and `hidden`. Parent directories may be
omitted; they are inferred only from existing descendants. Optional `status`
and `warnings` appear as a development notice.

`GET /files/<component-encoded-path>` serves the original file. The server owns
root containment, MIME types, download disposition, and media range handling.
Unsupported files are download-only in the UI. No external assets or services
are used. Text previews are bounded; PDFs use the browser's native renderer,
and videos use native controls.

Run the focused navigation checks with
`rtk proxy bun test pipelines/drive_preview/app.test.js`.


Static development exports may add `<meta name="ck-drive-manifest" content="drive.json">` to the page. Without it, the existing `/api/drive` contract remains unchanged. Assets resolve relative to the page. Inventory entries may set `url` and `download_url` to same-origin relative or root paths; omitted values retain the local file route. Exporters can give inert files a `.download` transport suffix without changing their inventory names.

An optional `downloads` array contains inventory path strings or `{ "path": "..." }` objects. Each must identify an actual, visible PDF with a known byte size. The mobile test section uses its original inventory name, size, open URL, and download URL. Attachment headers and original-byte copying belong to the exporter/host. This section supports physical-device testing; it does not certify phone performance or approve the development content.

Export a selected folder for static test hosting:

```sh
rtk proxy uv run ck export-preview --drive /path/to/example-files --output build/mobile-preview
```

The output is a self-contained Vercel static project. Only export an intentionally
small examples folder for online hosting; keep the expanding Variant 1 tree
local. Do not point a deployment helper at the repository, cache, or worktrees.
The exporter copies files byte for byte, records their sizes and SHA-256 hashes,
and gives active documents and programs an inert `.download` transport suffix.
Vercel's download route sends attachment headers. No credentials, host paths,
analytics, or external assets are required in the export.

If representative pages are extracted from this project's generated maps,
identify them as samples, retain the original attribution, remove links to
omitted pages, and record the original file hash and selected page numbers in
the build receipt. Do not alter third-party documents to create examples.
Sample files do not stand for complete county coverage or phone certification.
Provenance and development status use the quiet development-notes treatment;
navigation and instructions for opening and downloading remain normal text.
