# Rust source notices: verified facts and concrete remaining work

The initial filename detector missed 17 of the 465 pinned Rust registry
archives. Three already contain license text under other filenames. Original
upstream notice companions were recovered for 13 more package versions. For
`void 1.0.2`, the matching release source provides no additional notice file.
Four bounded cases still need the specific interpretation or notice work
described below: amplify_syn, objc2, cesu8, and void.

This audit changes no catalog entry, VERIFY marker, approval, or app selection.
The [evidence](evidence/bitchat-rust-notices.json) and
[companion/notice-copy proposals](evidence/bitchat-rust-notice-companions.json)
separate mechanical checks from actual remaining questions. The 11 proposed
original companion archives total 10,088,448 bytes. They are cached, unchanged,
by SHA-256; they are not new approved catalog pins.

## Facts already checked

The existing Rust source packet binds all 465 registry archive checksums to the
application's Cargo lockfile and publisher version metadata, including sizes
and declared license expressions. This audit independently rehashed all 465
cached archives and inspected every archive path for the initial detector's
notice filenames. It also inspected manifests, source headers, READMEs, and
embedded VCS metadata for the 17 missed packages.

The 448 filename matches and three alternate-name cases are inventory facts.
They do not establish that every per-file grant has been interpreted, that an
Android build used every lockfile package, or that the final drive delivers the
required notices. Repeating a request to verify known registry checksums would
add no evidence. Original app, Arti, and newly proposed Git source archives
without publisher archive checksums still need reviewed checksum pins under
AGENTS.md §7.

## What the 17 cases actually contain

| Package/version | Finding and action supported by original files |
| --- | --- |
| `priority-queue 2.7.0` | The registry archive already contains `LGPL-3.0-or-later.txt` and `MPL-2.0.txt`. The detector missed their names. Preserve these files; no replacement source archive is needed to recover them. |
| `r-efi 5.3.0`, `6.0.0` | Each registry archive's `AUTHORS` contains the full MIT grant/disclaimer, copyright notices, author list, and alternate license declarations. Preserve the actual file; the MIT notice is already present. |
| `amplify_num 0.5.4` | Embedded VCS commit binds the package to an upstream workspace with the omitted Apache `LICENSE`. Eight packaged nonmetadata files match, including the README referenced from the workspace parent. |
| `amplify_syn 2.0.1` | Eleven packaged files match its embedded VCS commit. Upstream supplies the Apache `LICENSE`; packaged source headers also contain a public-domain dedication and refer to MIT. Preserve these original declarations and resolve that specific per-file interpretation. |
| `anes 0.1.6` | Its older VCS record omits the workspace path. The `anes/` subdirectory at that exact commit matches 30 packaged files. Root `LICENSE-MIT` and `LICENSE-APACHE` are present upstream. |
| `asn1-rs-impl 0.2.0` | All three compared package files match `impl/` at the embedded commit. Upstream root contains both original license files. |
| `cookie-factory 0.3.3` | Twelve package files match its embedded commit. Upstream contains the omitted `LICENSES/MIT.txt`, including its original copyright line. |
| `derive-deftly-macros 1.6.0` | Thirty-four package files match `macros/` at the embedded commit. Upstream root `LICENCE` contains the original complete MIT notice. |
| `jni-sys-macros 0.4.1` | Three compared files match at the embedded commit. Root `LICENSE-MIT` and `LICENSE-APACHE` are present upstream. |
| `objc2-core-foundation 0.3.2`, `objc2-io-kit 0.3.2` | Their shared exact-commit `LICENSE.md` declares selectable licenses and an Apple SDK redistribution caveat. Respectively, 26 and eight packaged files match git. Generated files absent from git remain in the unchanged registry archives. The caveat needs a specific decision; the source companion does not remove it. |
| `valuable 0.1.1` | Twenty package files match the embedded commit, including the workspace-parent README. Root `LICENSE` contains its original complete MIT notice. |
| `cesu8 1.1.0` | Publisher commit `f18962a9…` matches all six packaged nonmetadata files and restores omitted `COPYRIGHT-RUST.txt`. The README's `LICENSE-RUST.txt` and the headers' full `LICENSE-MIT`/`LICENSE-APACHE` files are absent from that commit too. Retain actual source copyrights and the restored original notice, and supply authentic standard terms for the selected declared license. Do not invent copyright text. |
| `void 1.0.2` | Publisher tag `1.0.2`, commit `ab2f4dbb…`, matches all four nonmetadata files. Its README and manifest declare MIT, but no full original MIT notice file was recovered. This is the precise remaining notice question; the declared license is already known. |
| Windows import crates, `winapi-i686-pc-windows-gnu 0.4.0` and `winapi-x86_64-pc-windows-gnu 0.4.0` | Publisher commit `30ed8e3b…` matches all 2,807 build/source/import-library payload files across both packages. Each manifest differs only in version: git says `0.3.2`, the registry package says `0.4.0`. Root original license files are available. Record this source-equivalent companion and version-only difference without claiming an embedded release commit or a rebuilt `.a` file. |

Several registry archives include Cargo-generated lockfiles absent from their
upstream Git trees. Those original files remain available in the pinned registry
archives; that difference is recorded separately from source-file differences.

The later winapi `0.3.9` source was also inspected and has different build files
and import libraries. It is not substituted as corresponding source for the
`0.4.0` import packages. The publisher's later
[license-packaging change](https://github.com/retep998/winapi-rs/commit/fa4e2c5a6dc495c71e6031bdde2e52870ebf6fdf)
explains why a newer tree includes license files inside those package folders.

## Specific questions that remain

The exact objc2
[publisher license statement](https://raw.githubusercontent.com/madsmtm/objc2/7b1abfd750a2cacaea71d6a56ecfb83cb7de560b/LICENSE.md)
raises uncertainty about redistributing Apple-SDK-derived bindings. The affected
crate manifests identify Apple frameworks. This audit does not establish that
those target-specific packages were compiled into the Android library. Resolve
their inclusion and rights from the actual target/build and source-distribution
requirements; do not treat a Cargo lockfile alone as proof of Android use.

For `amplify_syn`, retain the actual Apache manifest/root-license declaration and
the different source-header wording for review. For `cesu8`, the missing named
full terms and recovered original copyright file are now known. For `void`, the
publisher's exact tag supplies no additional full notice. These are bounded
notice/grant-interpretation questions, not 465 unknown source licenses.

The proposed Git archive pins have no publisher archive checksum. Their HTTPS
bytes, source correspondence, original notice hashes, and proof URLs were
verified, but the pins still require the reviewed pull request specified by
AGENTS.md. No proposal clears an existing human/legal approval or the original
app/Arti pin requirements.

## Deliver original notices without editing publisher files

After the companion pins and specific questions are resolved, append the
proposed source-graph edges while preserving existing inputs. The proposal
records exact archive members, byte hashes, and separate drive paths under
`8_MESH_CHAT/LICENSES/bitchat/`. Copy those members unchanged, alongside a
project-authored index binding each copy to its package and archive checksum.
Keep the existing package archives unchanged, including generated files.

The current assembler writes mesh app `SOURCE.TXT` and top-level attributions;
it does not populate that dependency license directory. That is concrete notice
delivery work. The APK does contain some notice-named ZIP entries; this audit
records them and does not infer the absence of notices in compiled resources or
the app UI from filenames alone. Final notice delivery must use the resolved
Android build/source inventory and the applicable selected grants.
