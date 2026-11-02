# Draft phone copy index

`tools/build_copy_index.py` reads an actual manifest-verified tree and produces
`0_WHAT_TO_COPY.pdf`, its HTML, and an external receipt in a fresh output folder.
It never adds the index to the source tree or rewrites that tree's manifest.
Integration into a later inspection tree is a separate step.

Run in the pinned build container with read-only source, drive, and font-cache
mounts, using `--root`, `--drive`, `--cache`, `--output`, `--manifest-sha256`,
`--epoch`, and `--tool-image`. Only the output parent needs write access.
The source manifest, every indexed file, producer dependencies, actual font pins,
requested tool image, tool versions, epoch, and PDF hash are recorded.

Only actual PDF, MP4, and APK paths outside BACKUP are listed. The index excludes
itself and other formats. Full paths remain readable; internal folder links and
bookmarks navigate the index without depending on cross-file PDF support.
Keep existing source and license notices when sharing referenced folders.

The phone layout is 90×160 mm with 12 pt body text and one column. Its byte cap comes
from build configuration. Rendering and browser checks support development
inspection only; no emergency-content or physical-phone approval is implied.
