# Manifesto Source Registry

Scope: Tamil Nadu Legislative Assembly elections, 2021 and 2026.

## Current status

**No manifesto source has been verified yet.** `data/raw/manifestos/manifest.json` is intentionally empty.

A source may only be added to the manifest after all of these checks pass:

1. Open the source.
2. Confirm the document/page actually contains manifesto material.
3. Confirm the party and election year.
4. Confirm the language.
5. Confirm the document is complete where possible.

Source tiers and source types (`primary`, `secondary`, `archive`, `discovery_only`) follow
[docs/phase3/manifesto_source_policy.md](../phase3/manifesto_source_policy.md).

## Verified sources

_None._

## Rejected / unverified candidate URLs — do not use

These URLs were previously added to this registry and incorrectly marked "Verified".
They were never opened before being recorded, and they appear to have been constructed
from search-result summaries rather than found on the hosting sites. When the
acquisition pipeline requested them on 2026-10-04, every one returned **HTTP 404 (Not Found)**.
They are kept here only so they aren't re-added by mistake.

| Party | Election | Candidate URL | Result |
|---|---|---|---|
| TVK | 2026 | `https://tvkvijay.com/manifesto2026.pdf` | HTTP 404, unverified |
| DMK | 2026 | `https://opencity.in/data/tn-elections/dmk-manifesto-2026.pdf` | HTTP 404, unverified |
| DMK | 2021 | `https://tn234.org/wp-content/uploads/2021/03/DMK-Manifesto-2021-Tamil.pdf` | HTTP 404, unverified |
| AIADMK | 2021 | `https://tn234.org/wp-content/uploads/2021/03/AIADMK-Election-Manifesto-2021.pdf` | HTTP 404, unverified |

## Discovery leads (not sources)

Web searches suggest that the DMK released its 2026 manifesto on 2026-03-29 and that the TVK
released its manifesto on 2026-04-16. The party sites (`dmk.in`, `tvkvijay.com`) and
OpenCity may host copies. These are leads for manual discovery only and have **not** been verified.
