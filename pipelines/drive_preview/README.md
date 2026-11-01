# Development Drive Explorer

These assets are served by the local development server, never copied to a
production drive. They browse the actual selected file inventory. Viewport
presets are generic widths, not physical-phone acceptance evidence.

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
