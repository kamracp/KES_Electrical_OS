# Electrical Master Reference Register

Controlled inventory of every standard, code, guideline and manufacturer reference that KES Electrical OS may cite.
Rules (see AGENTS.md and ADR-0001):

- Only a record with `verification_status: VERIFIED` may support a `COMPLIANCE_READY` conclusion.
- `UNVERIFIED`, `UNRESOLVED`, `LEGACY` and `REFERENCE_ONLY` records may inform design checks but never statutory compliance.
- Editions and amendments are never inferred. A missing edition is a gap (see `reference-gap-register.md`), not a default.
- Records hold bibliographic metadata and non-copyrighted rule summaries only; no clause text is stored in this repository.
- Every engine that cites a reference does so by `reference_id` and clause locator, never by free text.

Precedence within a project (highest first): statutory/jurisdictional (CEA, state authority) → project design basis → national standards (IS/CPWD) → international standards (IEC/IEEE) → manufacturer certified data → `REFERENCE_ONLY` guidance.

Status vocabulary: `VERIFIED` | `UNVERIFIED` | `UNRESOLVED` | `LEGACY` | `REFERENCE_ONLY` | `SUPERSEDED`

## 1. Indian statutory and national references

| reference_id | Authority | Document | Part / edition / amendment | Jurisdiction / purpose | Precedence | Status | Impacted modules | Locator / notes |
|---|---|---|---|---|---|---|---|---|
| REF-CPWD-P1-2013 | CPWD, Govt. of India | General Specifications for Electrical Works Part I Internal | 2013 | India, internal installations | National | LEGACY | EOS-06, EOS-07, EOS-08, EOS-12 | Verified legacy source; superseded by 2023 for new work |
| REF-CPWD-P1-2023 | CPWD | General Specifications for Electrical Works Part I Internal | 2023 | India, internal installations | National | UNVERIFIED | EOS-06, EOS-07, EOS-08, EOS-12 | Required; controlled copy not yet registered with checksum in this repo |
| REF-CPWD-P2-2023 | CPWD | General Specifications for Electrical Works Part II External | 2023 | India, external/HT/substation | National | UNVERIFIED | EOS-03, EOS-07, EOS-08 | Required; controlled copy not yet registered with checksum in this repo |
| REF-CPWD-P3-P7 | CPWD | General Specifications Parts III (Lifts), IV (Substation), V (Wet risers/fire), VI (HVAC), VII (DG sets) + correction slips | editions per part — unresolved | India | National | UNRESOLVED | EOS-03, EOS-07, EOS-09 | Each part and correction slip needs its own record once acquired |
| REF-CPWD-SUBSTN | CPWD | Substation and Power Distribution guideline; CPWD Works Manual | edition unresolved | India | National | UNRESOLVED | EOS-03, EOS-07 | Applicability per project |
| REF-IS-2026 | BIS | IS 2026 Power transformers | parts/edition/amendment unresolved | India | National | UNVERIFIED | EOS-03 | Exact part list required before transformer compliance claims |
| REF-IS-3156 | BIS | IS 3156 Voltage transformers | parts/edition unresolved | India | National | UNVERIFIED | EOS-07, EOS-15 | |
| REF-IS-732 | BIS | IS 732 Code of practice for electrical wiring installations | edition/amendment unresolved | India | National | UNVERIFIED | EOS-06, EOS-08, EOS-12 | |
| REF-IS-3043 | BIS | IS 3043 Code of practice for earthing | edition/amendment unresolved | India | National | UNVERIFIED | EOS-08 | |
| REF-CEA-REG | CEA | Measures relating to Safety and Electric Supply Regulations | year/amendment unresolved | India, statutory | Statutory | UNRESOLVED | all | Statutory precedence once verified |

## 2. International standards

| reference_id | Authority | Document | Part / edition | Purpose | Precedence | Status | Impacted modules | Notes |
|---|---|---|---|---|---|---|---|---|
| REF-IEC-60287 | IEC | Electric cables — current rating | series; edition unresolved | Ampacity method | International | UNVERIFIED | EOS-06 | |
| REF-IEC-60364 | IEC | Low-voltage electrical installations | series; edition unresolved | Installation design | International | UNVERIFIED | EOS-02, EOS-06, EOS-08 | |
| REF-IEC-60364-5-52 | IEC | LV installations — selection and erection of wiring systems | edition unresolved | Cable installation methods, derating | International | UNVERIFIED | EOS-06, EOS-12 | |
| REF-IEC-60909-0 | IEC | Short-circuit currents in three-phase AC systems — calculation | edition UNRESOLVED | Fault calculation | International | UNRESOLVED | EOS-04, EOS-05, EOS-07 | Code string `IEC 60909-0:2026` in `fault` engine is NOT accepted as verified until checked against an official source |
| REF-IEC-60909-3 | IEC | Short-circuit currents — currents during two separate simultaneous line-to-earth short circuits | edition unresolved | Earth-fault | International | UNVERIFIED | EOS-04 | |
| REF-IEC-60947 | IEC | Low-voltage switchgear and controlgear | series; edition unresolved | Device ratings | International | UNVERIFIED | EOS-05, EOS-07 | |
| REF-IEC-60947-2 | IEC | LV switchgear — circuit-breakers | edition unresolved | Breaker duty, Icu/Ics | International | UNVERIFIED | EOS-05, EOS-07 | |
| REF-IEC-61439 | IEC | LV switchgear and controlgear assemblies | series; edition unresolved | Panel design verification | International | UNVERIFIED | EOS-07 | |
| REF-IEC-60255 | IEC | Measuring relays and protection equipment | series; edition unresolved | Relay characteristics (TCC) | International | UNVERIFIED | EOS-05 | |
| REF-IEC-62305 | IEC | Protection against lightning | series; edition unresolved | LPS design | International | UNVERIFIED | EOS-09 | |
| REF-IEC-61643 | IEC | Low-voltage surge protective devices | series; edition unresolved | SPD selection | International | UNVERIFIED | EOS-10 | |
| REF-IEEE-80 | IEEE | Guide for Safety in AC Substation Grounding | edition unresolved | Earth grid, touch/step | International | UNVERIFIED | EOS-08 | |
| REF-IEEE-242 | IEEE | Buff Book — protection and coordination | 2001 | Coordination guidance | International | LEGACY | EOS-05 | Supersession status by IEEE 3004.x series to be confirmed |

## 3. Reference-only guidance (never compliance evidence)

| reference_id | Publisher | Document | Edition | Status | Restriction | Impacted modules |
|---|---|---|---|---|---|---|
| REF-SE-EIG-2018 | Schneider Electric | Electrical Installation Guide | 2018 | REFERENCE_ONLY | Methodology illustration only; cite the underlying IEC clause | EOS-02..EOS-12 |
| REF-SE-0100DB2301 | Schneider Electric | Electrical Distribution Fundamentals Design Guide 0100DB2301 | March 2025 | REFERENCE_ONLY | US (NEC/ANSI) context; not applicable to Indian statutory conclusions | EOS-02, EOS-04, EOS-05 |
| REF-SE-WIKI | Schneider Electric | Electrical Installation Wiki (living) | rolling | REFERENCE_ONLY | Unversioned; capture page + date when cited | EOS-02..EOS-12 |
| REF-USER-LNKD | User-supplied | Electrical OS reference (https://lnkd.in/p/dzyAPdgr) | — | UNRESOLVED | Not captured; content unknown | — |

## 4. Manufacturer certified data

Project-specific certified data from Schneider, Siemens, ABB and L&T is consumed only through versioned adapters (ADR-0001) and recorded per project with document number, revision and date. No manufacturer data is bundled in this repository.

## 5. Record template (for every new or upgraded record)

```text
reference_id, authority/publisher, document number and title, part/section/edition/amendment/correction slip,
jurisdiction and project purpose, applicability and precedence, source URL or controlled locator,
file checksum and acquisition date, license/access status, verification status + verifier + date,
clause/table/figure/annex locator, non-copyrighted derived rule summary, encoded rule identifier(s),
impacted modules, effective and supersession dates, review and approval evidence
```

Records above carry only the fields known today; missing fields are gaps to be closed in `reference-gap-register.md`, never filled by assumption.

## 6. Change control

| Date | Change | By |
|---|---|---|
| 2026-09-15 | Register created from the controlled baseline in the Enterprise Master Prompt v2.0 §6; all statuses initial | KES |
