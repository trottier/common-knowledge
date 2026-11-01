# Frozen development archive checkpoints

These pairs use one source checkout and development epoch 1793404800. Each
pipeline ran in separate network-disabled Linux amd64 containers and checked
its original inputs, output payloads, and complete generation metadata. Human
review statuses remain unchanged.

| Item | Placed payload bytes | Canonical generation SHA-256 |
| --- | ---: | --- |
| WikEM, 4,278 articles and 6,641 redirects | 8,601,054 | d735e2f7b9278e5bd0a5d4850a9d07ab2437eb170b6c8b38553f36254951319a |
| English Wikibooks, 131,815 entries | 3,333,493,444 | 380802c9641775e657d43a696041491a326b899c7bd451c73b7a85f229b9ebc1 |
| Simple English Wikipedia, 405,521 entries | 790,886,776 | 95e45905039855bea0431f7919ccd7676315e6c79b70da2cce7d806ed417c591 |
| English Wikivoyage, 68,381 entries | 205,100,489 | a684c7adb661985250bdfa4c1dfb47518406a230d279e4a7efc510eeabfab1cd |
| English WikiMed, 377,179 entries | 753,161,276 | 7420c007141a58f2e549c7d2cbe41d9b9356d4dea4e229333db89e133e897355 |
| Medical phone PDFs, 158 articles, before equation rendering | 69,972,915 | 7944c1711a987aaab48a8ad78cf14b640b68d91c7871a7e860224ec229fd1f74 |

The medical row is a historical repeat checkpoint. The later equation-preserving
pack is 70,054,021 placed bytes with generation SHA-256
`cdff7b842c7580f45454fc19752d7117f1b52b17813938b0911cd2055bb5a375`.
Its independent repeats and remaining clinical/device gates are recorded in
[math-rendering.md](math-rendering.md). Do not reuse the older medical pin.

WikEM, Wikibooks, Simple English Wikipedia, Wikivoyage, and WikiMed pass strict
`zimcheck`. WikiMed repairs three audited malformed internal links. Its two
builds and canonical copy match, including all nine recorded payload and audit
file hashes; see [the repeat evidence](evidence/wikimed-repeat.json).
Wikibooks repairs the audited missing
favicon/resources without changing publisher article text or valid local
resources; source downloads remain byte-identical. The title index is retained;
the publisher's full-text index is not carried into regenerated archives.
The whole Wikibooks archive also includes administrative and general-interest
material, so a school-curriculum or age-suitability approval is not claimed.

The medical selection remains a draft, including its eight canonical WikEM
topics. Repeated hashes establish reproducibility, not clinical correctness.
Stable source hosting, license/pin review, physical reader/device tests, and
reproduction at the final release epoch remain open. These checkpoints do not
establish full-profile completion.
