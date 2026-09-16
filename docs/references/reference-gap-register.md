# Reference gap register

Tracks missing editions, amendments, evidence, licences and applicability decisions for the
references listed in `electrical-master-reference-register.md`. A gap marked "blocks
COMPLIANCE_READY" prevents any calculation citing that reference from being reported as
compliance-ready until the gap is closed. Design-check results are still produced and carry
the corresponding engineering warning.

KES Electrical OS is a global, vendor-neutral product. References are scoped to jurisdiction
profiles (for example IN, IEC, US, UK, AU-NZ, EU); a reference is never "inapplicable" in
general, only outside its profile. Product data is identified by product class, specification
and rating, never by manufacturer name. The precedence order in the master register is the
IN profile until GAP-012 introduces the profile model.

Status values: OPEN, IN_PROGRESS, CLOSED (with closing commit).

| Gap ID | Related reference(s) | Gap type | Description | Affected capability / code | Blocks COMPLIANCE_READY | Closing action | Status |
|---|---|---|---|---|---|---|---|
| GAP-001 | REF-CPWD-P1-2023, REF-CPWD-P1-2023-AMD | Clause mapping | Part I Chapter 18 (Tables 1 to 11-D) and the cable clauses of Chapter 3 are verified as documents but no table or clause is yet mapped into the reference data layer with edition and checksum | EOS-06 `cable_engine.py` (tabulated ampacity is an approximation; derating factors must be established independently) | Yes (IN profile) | Map the specific tables clause-by-clause into reference data; independent engineering review; then retire the approximation for the IN profile | OPEN |
| GAP-002 | REF-CPWD-P4-2013 | Controlled copy | Part IV Sub Station 2013 edition confirmed on cpwd.gov.in but not downloaded or checksummed | EOS-03, EOS-07, EOS-08 | Yes (IN profile) | Download from the CPWD publication page, record SHA-256 in the register and `docs/standards/01_CPWD/README.md` | OPEN |
| GAP-003 | REF-CPWD-P7-2013 | Controlled copy + amendment | Part VII DG Sets 2013 and its Amendment dated 05.11.2024 confirmed but not downloaded or checksummed | EOS-03 generator sizing | Yes (IN profile) | Download both, register both checksums, record amendment precedence | OPEN |
| GAP-004 | REF-CPWD-P1-2013, all profiles | Design basis | Projects must state the governing jurisdiction profile and the governing edition of each national reference (for IN: CPWD 2013 LEGACY vs 2023 + Amendments) | EOS-01 design basis | No | Design-basis fields for jurisdiction profile and governing editions; default for IN new work is 2023 + Amendments | OPEN |
| GAP-005 | REF-IEC-60364-5-52 | Edition unresolved | Edition not resolved; cable engine cites it as `standard_reference` without a verification status | EOS-06, IEC/IN/UK/EU profiles | Yes | Resolve edition, register controlled copy or licence evidence, then close GAP-010 | OPEN |
| GAP-006 | REF-IEC-60287 | Edition unresolved | Ampacity method reference cited by the cable engine (`ampacity_reference`) with no edition or evidence | EOS-06 | Yes | Resolve edition and parts in use; register evidence | OPEN |
| GAP-007 | REF-IEC-60909-0 | Unverified edition string | Fault engine carries the literal `IEC 60909-0:2026`; that edition is not accepted as verified | EOS-04 `fault` engine | Yes | Replace with the resolved edition from the register once verified; add a test that the engine string equals the register entry | OPEN |
| GAP-008 | (not yet registered) IS 3961 series, IS 1554, IS 7098 | Missing register entries | Indian cable standards referenced by CPWD Part I for conductor ratings and cable construction are not in the master register | EOS-06, IN profile | Yes (IN profile) | Add register rows with edition status; national tier outranks IEC within the IN profile | OPEN |
| GAP-009 | REF-SE-EIG-2018, REF-SE-WIKI, REF-SE-0100DB2301 | Vendor neutrality | Manufacturer-authored literature is named in the register. Product rule: no manufacturer name appears in engines, contracts, UI, warnings or reports; such literature may serve only as a development-time methodology cross-check with the underlying standard clause cited; product data is keyed by product class, specification and rating, with any vendor identity confined to project-supplied datasheet metadata | register, golden-case register, planned `product_data/` adapters (ADR-0001) | No | Replace named rows with one generic "manufacturer technical literature (unnamed)" REFERENCE_ONLY row; rename `manufacturers/` to `product_data/` in the target structure; add a test that no vendor name string exists under `backend/app` or `frontend/src` | OPEN |
| GAP-010 | all engine `standard_reference` fields | Contract gap | Calculation responses carry reference strings with no verification status or profile, so UNVERIFIED references render without a marker in the UI | API contracts, frontend result panels | Yes | Add `reference_verification_status` (and profile) to backend response contracts; mirror in frontend zod schemas and panels | OPEN |
| GAP-011 | ADR-0001 vs README capability map | ID reconciliation | 17-module ADR numbering vs canonical 15-module EOS map; IDs must not be mixed | documentation, `enterprise-capability-map.md` | No | Controlled documentation milestone reconciling ADR-0001 to EOS-01..15 | OPEN |
| GAP-012 | master register precedence (line "Precedence within a project"), Master Prompt v2.0 §3 | Jurisdiction profile model | Precedence, reference ambient conventions, voltage/frequency defaults and compliance vocabulary are hard-coded to India; a global product needs a jurisdiction profile selected in the design basis, with references and precedence scoped per profile | EOS-01, all engines' reference fields, register structure, Master Prompt (needs v2.1 amendment) | Yes (for any non-IN project) | ADR for jurisdiction profiles; profile column in the master register; design-basis profile field and UI selection; engines read limits/references through the profile | OPEN |
| GAP-013 | REF-IEC-60364-5-52, REF-IEC-60287, jurisdiction profiles | Profile-derived references | `standard_reference` and `ampacity_reference` are request defaults, so a US or AU-NZ profile still reports IEC 60364-5-52 / IEC 60287 in the References panel (seen in the 17 Sep smoke; safe only because the Unresolved status is shown beside it) | EOS-06 cable contract, `jurisdiction_profiles.py` | Yes (non-IN/IEC profiles) | Add `governing_references` to the profile registry; engines take references from the profile, the request fields become optional overrides recorded as deviations | OPEN |

## Closed gaps

| Gap ID | Description | Closing commit | Date |
|---|---|---|---|
| GAP-000 | CPWD Part I 2023, Part I 2023 Amendments and Part II 2023 controlled copies registered with SHA-256 from the official CPWD publication page; Parts III to VIII editions resolved | `6e82126`, `88e30ab` | 2026-09-16 |
