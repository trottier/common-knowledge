# Frozen development archive checkpoints

These pairs use one source checkout and development epoch 1793404800. Each
pipeline ran in separate network-disabled Linux amd64 containers and checked
its original inputs, output payloads and complete generation metadata. Human
review statuses remain unchanged.

| Item | Placed payload bytes | Canonical generation SHA-256 |
| --- | ---: | --- |
| WikEM, 4,278 articles and 6,641 redirects | 8,601,054 | d735e2f7b9278e5bd0a5d4850a9d07ab2437eb170b6c8b38553f36254951319a |
| English Wikibooks, 131,815 entries | 3,333,493,444 | 380802c9641775e657d43a696041491a326b899c7bd451c73b7a85f229b9ebc1 |
| Medical phone PDFs, 158 articles | 69,972,915 | 7944c1711a987aaab48a8ad78cf14b640b68d91c7871a7e860224ec229fd1f74 |

WikEM and Wikibooks pass strict `zimcheck`. Wikibooks repairs the audited missing
favicon/resources without changing publisher article text or valid local
resources; source downloads remain byte-identical. The title index is retained;
the publisher's full-text index is not carried into regenerated archives.
The whole Wikibooks archive also includes administrative and general-interest
material, so a school-curriculum or age-suitability approval is not claimed.

The medical selection remains a draft, including its eight canonical WikEM
topics. Repeated hashes establish reproducibility, not clinical correctness.
Stable source hosting, license/pin review, physical reader/device tests and
reproduction at the final release epoch remain open. Other archive pairs are
still running; these checkpoints do not establish full-profile completion.
