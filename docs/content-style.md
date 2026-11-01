# Content and review

Use short, direct sentences and one action per line. State when an action should
not be taken. Medical and rescue procedures must include a branch for an
unanswered 911 call; a placeholder does not count as an approved protocol.

Each Markdown source carries `status`, `reviewer` and `reviewed_on`. The agent
does not approve content. Release validation must require a named human reviewer
for medical, legal and radio material, and must reject unresolved markers.

Factual claims use `[@source_id]` references defined in `content/sources.yaml`.
Write multiple references separately, such as `[@first_source] [@second_source]`.
Grouped references, empty IDs and unfinished references fail rendering and
release checks. Every edition is checked, including machine translations.
Original wording summarizes sources; third-party publications are fetched
separately, unchanged and only after catalog license verification.

Coordination values render from `config/defaults.yaml`. Generated START and card
HTML carry the same inert JSON copy of those defaults for cross-edition checks.
The visible text uses the same configuration values. Unresolved development
instructions are highlighted; no placeholder is an instruction to improvise.

The English edition remains a draft until human review. Spanish and all other
machine editions must show their localized unreviewed-translation footer on
every page. Device-specific instructions also need physical device testing.
