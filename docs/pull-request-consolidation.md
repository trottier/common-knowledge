# Pull request consolidation

The development work accumulated as a stack of draft PRs. The current implementation
is consolidated in [PR #40](https://github.com/trottier/common-knowledge/pull/40).
The earlier PRs below are superseded review records. Their branches are retained.

The audit checked commit ancestry and patch equivalence. For cherry-picks with
regenerated reports or later catalog changes, it mapped the corresponding integration
commit and compared the changed catalog fields. All changed catalog values were
present in the corresponding integrated commit. The archive-cleanup code difference
is the later audited favicon fix, which is retained in the integration branch.
Documentation differences retain later measured checkpoints and review gates.
No unique implementation change was found in the superseded PRs.

This consolidation preserves draft content status, source/license holds, and the
sample/full build and physical-device requirements. A development code merge grants
no human clinical, utility, radio, legal or source-pin review status.

| PR | Original branch | Inclusion evidence |
| --- | --- | --- |
| [#8](https://github.com/trottier/common-knowledge/pull/8) | `work/08-directory` | Commit ancestry |
| [#9](https://github.com/trottier/common-knowledge/pull/9) | `work/spec-alignment` | Commit ancestry |
| [#10](https://github.com/trottier/common-knowledge/pull/10) | `work/09-atlas` | Commit ancestry |
| [#11](https://github.com/trottier/common-knowledge/pull/11) | `work/10-android-maps` | Commit ancestry |
| [#12](https://github.com/trottier/common-knowledge/pull/12) | `work/11-medical-pdfs` | Commit ancestry |
| [#13](https://github.com/trottier/common-knowledge/pull/13) | `work/12-local-llm` | Commit ancestry |
| [#14](https://github.com/trottier/common-knowledge/pull/14) | `work/13-imports` | Commit ancestry |
| [#15](https://github.com/trottier/common-knowledge/pull/15) | `work/14-release` | Commit ancestry |
| [#16](https://github.com/trottier/common-knowledge/pull/16) | `work/15-national` | Commit ancestry |
| [#17](https://github.com/trottier/common-knowledge/pull/17) | `work/16-apps` | Commit ancestry |
| [#18](https://github.com/trottier/common-knowledge/pull/18) | `work/17-sources` | Commit ancestry |
| [#19](https://github.com/trottier/common-knowledge/pull/19) | `work/18-geography` | Commit ancestry |
| [#20](https://github.com/trottier/common-knowledge/pull/20) | `work/19-osmand` | Commit ancestry |
| [#21](https://github.com/trottier/common-knowledge/pull/21) | `work/20-atlas-national` | Commit ancestry |
| [#22](https://github.com/trottier/common-knowledge/pull/22) | `work/21-android-national` | Commit ancestry |
| [#23](https://github.com/trottier/common-knowledge/pull/23) | `work/22-font-coverage` | Commit ancestry |
| [#24](https://github.com/trottier/common-knowledge/pull/24) | `work/23-laptop-map` | Commit ancestry |
| [#25](https://github.com/trottier/common-knowledge/pull/25) | `work/24-national-directory` | Commit ancestry |
| [#26](https://github.com/trottier/common-knowledge/pull/26) | `work/25-android-filter` | Patch-equivalent commits |
| [#27](https://github.com/trottier/common-knowledge/pull/27) | `work/27-android-policy` | Mapped integration commits; metadata/source differences audited |
| [#28](https://github.com/trottier/common-knowledge/pull/28) | `work/28-directory-links` | Mapped integration commits; metadata/source differences audited |
| [#29](https://github.com/trottier/common-knowledge/pull/29) | `work/26-atlas-determinism` | Patch-equivalent commits |
| [#30](https://github.com/trottier/common-knowledge/pull/30) | `work/29-card-qr` | Commit ancestry |
| [#31](https://github.com/trottier/common-knowledge/pull/31) | `work/30-wikem-api` | Mapped integration commits; metadata/source differences audited |
| [#32](https://github.com/trottier/common-knowledge/pull/32) | `work/31-reference-collections` | Mapped integration commits; metadata/source differences audited |
| [#33](https://github.com/trottier/common-knowledge/pull/33) | `work/32-morale-books` | Commit ancestry |
| [#34](https://github.com/trottier/common-knowledge/pull/34) | `work/33-video-captions` | Commit ancestry |
| [#35](https://github.com/trottier/common-knowledge/pull/35) | `work/35-territory-sources` | Mapped integration commits; metadata/source differences audited |
| [#36](https://github.com/trottier/common-knowledge/pull/36) | `work/36-morale-music-games` | Mapped integration commits; metadata/source differences audited |
| [#37](https://github.com/trottier/common-knowledge/pull/37) | `work/37-source-bundles` | Patch-equivalent commits |
| [#38](https://github.com/trottier/common-knowledge/pull/38) | `work/38-zim-resources` | Patch-equivalent commits |
| [#39](https://github.com/trottier/common-knowledge/pull/39) | `work/34-integration` | Commit ancestry |
| [#41](https://github.com/trottier/common-knowledge/pull/41) | `work/40-android-repro` | Mapped integration commits; metadata/source differences audited |
| [#42](https://github.com/trottier/common-knowledge/pull/42) | `work/42-medical-draft` | Patch-equivalent commits |
| [#43](https://github.com/trottier/common-knowledge/pull/43) | `work/43-input-workflow` | Patch-equivalent commits |
| [#44](https://github.com/trottier/common-knowledge/pull/44) | `work/45-official-translations` | Patch-equivalent commits |
| [#45](https://github.com/trottier/common-knowledge/pull/45) | `work/41-archive-freeze` | Mapped integration commits; metadata/source differences audited |
| [#46](https://github.com/trottier/common-knowledge/pull/46) | `work/46-reference-packs` | Mapped integration commits; metadata/source differences audited |
| [#47](https://github.com/trottier/common-knowledge/pull/47) | `work/47-federal-mental-health` | Patch-equivalent commits |
| [#48](https://github.com/trottier/common-knowledge/pull/48) | `work/49-reference-fonts` | Mapped integration commits; metadata/source differences audited |
| [#49](https://github.com/trottier/common-knowledge/pull/49) | `work/48-caption-alignment` | Mapped integration commits; metadata/source differences audited |
| [#50](https://github.com/trottier/common-knowledge/pull/50) | `work/51-shutoff-draft` | Patch-equivalent commits |
| [#51](https://github.com/trottier/common-knowledge/pull/51) | `work/53-citation-validation` | Patch-equivalent commits |
| [#52](https://github.com/trottier/common-knowledge/pull/52) | `work/54-llm-context` | Patch-equivalent commits |
| [#53](https://github.com/trottier/common-knowledge/pull/53) | `work/55-dev-checkpoint` | Patch-equivalent commits |
