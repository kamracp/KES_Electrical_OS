# Standards & Reference Library — Sourcing Status

This tree mirrors the structure you specified. It is scaffolding: folders exist so
files land in the right place as they're acquired, but **no full copyrighted
documents are bundled into this repository** — see "Why" below. Each numbered folder
has its own `SOURCE_STATUS.md` with what's actually free vs. paid and the official
place to get it.

## Why documents aren't pre-loaded here

Almost everything in this tree is copyrighted:

* **CPWD** publications carry an explicit "all rights reserved, no reproduction"
  notice even though CPWD itself hosts them free-to-read on `cpwd.gov.in`.
* **BIS (IS codes)** are legally binding documents; BIS's own "Know Your Standard"
  portal gives free *viewing* access, but that is not the same as a license to copy
  or redistribute.
* **IEC and IEEE standards are commercial** — sold by the standards bodies, not
  freely available anywhere legitimate.
* **NFPA codes** offer free online *read* access on nfpa.org; downloadable/printable
  copies are commercial.
* **Manufacturer guides** (Schneider, Siemens, ABB, Legrand, LS) are usually free to
  download as technical/marketing literature, but remain the manufacturer's
  copyrighted content.

I will not download, store, or reproduce full copyrighted documents — including ones
that are free to *view* — into this repository or into chat. What I *can* do, and
have started doing (see `01_CPWD/cpwd_seed_records.json`), is extract factual,
non-copyrightable **bibliographic metadata** (standard code, title, issuing body,
edition, publication year, official URL) from official sources and load that into
the Standards Registry (`EOS-02`), exactly as `KESE-S1-M3`'s CRUD already supports.

## Sourcing status by folder

| Folder | Status | Legitimate source |
|---|---|---|
| `01_CPWD` | Free to read (official) | `cpwd.gov.in/Publication` |
| `02_NBC_2016` | Free to read (official, published as a BIS Special Publication) | `bis.gov.in` |
| `03_CEA` | Free, statutory (Gazette-published regulations) | `cea.nic.in` |
| `04_BIS_IS` | Free to *view* via BIS's own portal; copying/redistribution restricted | `bis.gov.in` → "Know Your Standard" |
| `05_IEC` | **Commercial** — no free legitimate source | IEC Webstore |
| `06_IEEE` | **Commercial** — no free legitimate source | IEEE Xplore / Techstreet |
| `07_NFPA` | Free online *read* access (registration); downloads are commercial | `nfpa.org` free access program |
| `08_Schneider` | Usually free technical/marketing literature | `se.com` resource library |
| `09_Siemens` / `10_ABB` / `11_Legrand` / `12_LS` | Usually free technical literature | respective manufacturer sites |
| `13_Literature`, `14_Calculation_Guides`, `15_KES_Knowledge_Base` | Your own curated material — no sourcing constraint | — |

## How to actually populate this

1. **You supply the PDF/document** (upload it in chat) → I extract structured
   metadata and, where useful, non-verbatim engineering-method summaries, and load
   them into the Standards Registry. The source file itself stays with you, not
   duplicated into this repo.
2. **You point me at an official free source** (a `bis.gov.in`, `cpwd.gov.in`,
   `cea.nic.in`, `nfpa.org`, or manufacturer URL) → I can fetch and extract metadata
   the same way, citing the official page.
3. For commercial-only sources (IEC, IEEE) I can tell you exactly which document
   number/edition you need and where to buy it, but cannot obtain the text itself.
