# System skill: handover-pc-system

**Job:** End-to-end residential Practical Completion and handover workflow. Orchestrates seed loading, evidence sweep, PC checklist execution, defects walk management, BASIX final certificate confirmation, HOW certificate handover, O&M pack assembly, final claim release, and DLP tracking setup. Produces a PC checklist and handover pack under `09-handover-dlp/` using `markdown-draft-for-review`, then opens the defects register in `07-construction/11-defects/` using `register-row-draft`.

This is the **fourth system skill in SiteWise**, inheriting the `seed-targeted-read` → `evidence-sweep` → content atomics → drafts → registers → return-summary skeleton documented in `contract-setup-system.md §"Skill skeleton — for slices 06+ to inherit"` and repeated in `cost-plan-system.md §"Skill skeleton inheritance"`. Slice 13 is the handover and DLP end of the SiteWise lifecycle; this skill closes the construction phase and opens the DLP tracking phase.

This skill enforces the §2 three-overlay declaration gate at its pre-flight. It enforces §register-discipline at every defect row boundary. It enforces the markdown-first review discipline before any handover pack is considered complete. None of these are negotiable.

## When called

Called by:
- the agent when the user asks to run or prepare for practical completion, PC walk, OC application, or handover;
- the agent when the user asks to hand over the HOW certificate, O&M manuals, warranties, or keys;
- the agent when the user asks for a defects walk, defects register, or DLP advice;
- the agent when the user asks to release the final claim or PC progress claim;
- the agent when the user asks to set up or review DLP tracking;
- as a re-run during the DLP period when defect notices are being managed or a DLP review is due.

The skill is **idempotent** for the DLP-review mode — re-running on a project with an existing PC checklist and open defects register refreshes open rows rather than duplicating.

## Caller passes

- **Active project folder path** — required.
- **Mode** — one of `pc-checklist` (run the full PC checklist and set up DLP tracking), `dlp-review` (review open defects register and DLP milestone status), or `advice-only` (conversational guidance only, no file written). Required unless the user's request makes it obvious.
- **Subject focus (optional)** — narrower task subject, e.g. "BASIX final certificate" or "defects walk only" or "HOW handover". The skill defaults to the full PC checklist if no narrower subject is passed.

The skill reads everything else it needs from the project folder.

## Pre-flight — Step 0: §2 declaration gate

Before any work:

1. Read the project `README.md` frontmatter.
2. Confirm `archetype`, `user_role`, and `state` are declared and not missing, blank, or `TBC` (per `../../AGENTS.md §2` and `../../00-doctrine/doctrine.md §seed-consultation-discipline`).
3. **If any is missing, blank, or `TBC`:** **stop**. Return:
   > Cannot produce a PC checklist or DLP record: the README is missing one or more required overlay declarations. Please declare `archetype`, `user_role`, and `state` in the frontmatter before any phase-gate work. Per `../../AGENTS.md §2` and `../../00-doctrine/doctrine.md §seed-consultation-discipline`, the agent does not guess these from project name, address, budget, site, or any other proxy.
4. **Do not load any seed, do not run evidence-sweep, do not draft.** The gate is binary.

The gate is enforced at the system-skill level **and** at the seed-loading boundary (`../atomic/seed-targeted-read.md` also enforces it). The redundancy is intentional.

If the user is mid-flow and wants the gate bypassed, the gate is **not** bypassed. Offer to help complete the declaration, but do not proceed with handover work until it is complete.

## Steps

### Step 1 — seed-targeted-read

Invoke `../atomic/seed-targeted-read.md` with task subject `residential PC handover` (or the caller's narrower subject focus).

The skill loads:

- **Tier 2 archetype seed** — one of `new-dwelling-guide.md`, `renovation-guide.md`, `multi-dwelling-guide.md`, `ancillary-guide.md`, or `small-commercial-guide.md` per `archetype:`.
- **Tier 3 role overlay** — one of `role-builder.md`, `role-architect-pm.md`, `role-owner-builder.md`, or `role-d-and-c.md` per `user_role:`. The role overlay carries the role-divergent handover responsibilities (who issues PC, who certifies OC, who holds HOW certificate, who assesses the final claim).
- **Required cross-cutting seeds** — required for PC handover work:
  - `defects-and-dlp-guide.md` — required; residential defects catalogue, DLP mechanics, role-aware warranty obligations, defect tracking schema;
  - `sustainability-energy-guide.md` — required; the BASIX final certificate is a mandatory hold point before OC and must be confirmed at the PC walk (see that seed §5 for the hold point workflow);
  - `contract-administration-guide.md` — required; final claim mechanism, certificate trigger, PC definition in the contract, defect notice clause references.
- **Conditional cross-cutting seeds** — loaded if the task subject signals:
  - `program-scheduling-guide.md` if open EOT claims or programme disputes are unresolved at PC;
  - `cost-management-principles.md` if the final claim involves unresolved PC sum reconciliations or variation close-out.
- For non-NSW states, the agent **flags state-coverage gaps** where the seeds reference NSW-specific instruments without callouts (per `../../AGENTS.md §8`). Common gaps for handover work: HOW/HBCF (NSW) vs DBI (VIC) vs QBCC HWI (QLD); BASIX final certificate (NSW) vs NatHERS/Section J compliance evidence (other states); LSL receipt as a consent condition.

The loaded seed list is held for `seed_consulted:` frontmatter on every deliverable this skill produces.

### Step 2 — evidence-sweep

Invoke `../atomic/evidence-sweep.md` with task subject `residential PC handover` (or the caller's narrower subject focus).

For a PC handover task, the sweep returns high-relevance artefacts including:

- the executed head contract in `07-construction/02-fioa-contract/` — defines PC, the defects schedule mechanism, final claim trigger, DLP period;
- the current cost plan and variation register in `01-cost/` and `07-construction/06-variations/` — for final claim and PC reconciliation;
- the BASIX certificate and BASIX final certificate in `04-planning-and-authorities/` — **BASIX final certificate is a hold point: OC cannot issue without it**;
- the HOW/HBCF certificate in `04-planning-and-authorities/` — must be in hand before PC is certified;
- consent conditions register — all conditions must be evidenced before OC application;
- inspection records in `07-construction/12-reports/` — all mandatory hold-point inspections (frame, waterproofing, final) must be attended and passed;
- stormwater/OSD completion certificate in `04-planning-and-authorities/` where required by consent conditions;
- plumbing, electrical, and gas compliance certificates where services installed;
- existing defects register in `07-construction/11-defects/` — all pre-PC defects must be reviewed for status;
- O&M manuals and product warranties — confirm location and completeness before handover.

Medium-relevance: consultant appointment completion certificates, subcontractor completion records and insurance certificates, photos of final works, programme milestone records.

Low: routine correspondence, pre-construction documents, early-stage planning materials.

The sweep also returns a **gap report** — expected-but-missing artefacts. Common gaps at handover: BASIX final certificate not yet obtained (OC blocker — flag immediately); HOW certificate missing or expired; unresolved hold points in the inspection record; open defects with no rectification date; consent conditions outstanding.

### Step 3 — Confirm mode with the project lead

Before producing any draft, confirm the mode with the user (caller may have specified at invocation):

- **`advice-only`** — produce conversational commentary or a structured response. No file written. Used when the user wants quick handover guidance (e.g. "what do I need to check before calling PC?") without creating a draft.
- **`pc-checklist`** — execute the PC checklist (Step 4), set up DLP tracking (Step 5), produce the handover pack markdown (Step 6), and surface gaps and escalations (Step 7).
- **`dlp-review`** — review the existing defects register and DLP milestone status. Refresh open defect rows. Surface overdue items. No new PC checklist produced unless the user requests one.

Mode `advice-only` returns at Step 3 with conversational commentary. Modes `pc-checklist` and `dlp-review` proceed to Step 4.

### Step 4 — Execute PC checklist

Mode `pc-checklist` executes the full checklist. Each item carries a status: **✓ complete**, **⏳ pending — action required**, or **✗ hold — OC or PC blocked until resolved**.

#### PC Checklist (~21 items)

| # | Item | Status |
|---|---|---|
| 1 | **Site clean and demobilisation** — builder has removed plant, scaffolding, surplus materials, and site shed. Site presented clean. | ✓ / ⏳ / ✗ |
| 2 | **Defects walk** — attended by builder, superintendent or certifier (where applicable), and owner. Date and attendees recorded. Written defects schedule produced. | ✓ / ⏳ / ✗ |
| 3 | **Defects register opened** — all defects from the walk logged in `07-construction/11-defects/` using `register-row-draft` (Df-seq). Each row carries trade, location, severity, date identified, photo reference. | ✓ / ⏳ / ✗ |
| 4 | **Critical defects rectified** — structural, waterproofing, life-safety, and access defects resolved before PC is called. Non-critical deferred defects listed on a defects schedule appended to the PC certificate. | ✓ / ⏳ / ✗ |
| 5 | **BASIX final certificate** — obtained from licensed NatHERS assessor or certifier confirming all BASIX-committed items installed as specified. **Hold point: OC cannot issue without this certificate.** Load `../../01-seed/sustainability-energy-guide.md §5` for the full BASIX final certificate workflow and evidence requirements. | ✓ / ⏳ / **✗ HOLD** |
| 6 | **OC application** — Occupation Certificate application lodged with the certifier or BPA. All conditions of consent evidenced and submitted. Stormwater / OSD, fire safety, pool safety certificates attached where applicable. | ✓ / ⏳ / ✗ |
| 7 | **HOW certificate handover** — original HOW/HBCF certificate of insurance handed to owner. Certificate currency date confirmed (must cover the full warranty period). Owner's name and site address correct on certificate. | ✓ / ⏳ / ✗ |
| 8 | **Pool safety certificate** (if applicable) — issued by accredited pool safety inspector. Copy provided to owner and lodged with council (NSW: required before occupation). | ✓ / ⏳ / N/A |
| 9 | **Fire safety statutory certificate** (if applicable — Class 1b, multi-dwelling, or where fire safety measures are installed) — issued by accredited fire safety practitioner. | ✓ / ⏳ / N/A |
| 10 | **Structural engineer hold points resolved** — all outstanding engineering hold-point inspections attended, signed off, and compliance certificates on file in `07-construction/12-reports/`. | ✓ / ⏳ / ✗ |
| 11 | **Plumbing compliance certificate** — issued by licensed plumber. Sydney Water (NSW) or state utility authority approval obtained. Copy in `04-planning-and-authorities/`. | ✓ / ⏳ / ✗ |
| 12 | **Electrical certificate of compliance** — issued by licensed electrician for all electrical work. CCEW (Certificate of Compliance Electrical Work) on file. | ✓ / ⏳ / ✗ |
| 13 | **Gas compliance certificate** (if gas services installed) — issued by licensed gasfitter. All gas appliances commissioned and tested. | ✓ / ⏳ / N/A |
| 14 | **Stormwater / OSD completion certificate** — where required by council or consent condition, OSD system inspected and completion certificate obtained. | ✓ / ⏳ / N/A |
| 15 | **Council infrastructure contributions** — all s. 7.11 (formerly s. 94) contributions, Long Service Levy (LSL) receipt, and any other consent-condition financial requirements paid and receipts on file in `04-planning-and-authorities/`. | ✓ / ⏳ / ✗ |
| 16 | **As-built drawings / mark-ups** — compiled and handed to owner. Where consultant drawings exist, confirm the design consultant's as-built obligation per their appointment. | ✓ / ⏳ / ✗ |
| 17 | **O&M manuals and warranties** — all manufacturer O&M manuals (appliances, plant, mechanical systems) and product warranties compiled into a single handover pack. Owner confirms receipt. | ✓ / ⏳ / ✗ |
| 18 | **Keys, remotes, and access devices** — keys (all sets), garage remotes, alarm PIN/fob, meter box keys, and any other access devices counted and handed to owner. Count recorded. | ✓ / ⏳ / ✗ |
| 19 | **Owner induction** — owner inducted on mechanical plant (HW system, HVAC, ventilation), switchboard location and circuit labelling, alarm panel, gas isolation, water isolation, any building management or smart-home systems. | ✓ / ⏳ / ✗ |
| 20 | **Final claim (PC progress claim) submitted** — PC claim issued by builder with PC certificate attached (or issued simultaneously). Amount per the contract PC stage schedule. Claim format per contract progress claim requirements. | ✓ / ⏳ / ✗ |
| 21 | **PC certificate issued** — PC certificate issued by superintendent (if applicable) or certifier, or acknowledged by owner per the contract terms. **Date of PC certificate is the DLP commencement date** — record in the project register and programme. | ✓ / ⏳ / ✗ |

**Checklist scoring:** If any item is `✗ hold`, PC should not be called and the final claim should not be released until the hold is resolved. The agent surfaces held items explicitly at Step 7.

The skill does not mark checklist items complete on the agent's assessment alone — it populates status based on the evidence found at Step 2 and prompts the project lead to confirm each item.

### Step 5 — DLP tracking setup

Mode `pc-checklist` only (and on explicit request in `dlp-review` mode when no DLP tracking exists).

After the PC certificate date is confirmed:

1. **Calculate DLP end date** from the PC certificate date and the DLP period in the contract Particulars. Flag if the contract DLP period is not stated — the skill does not assume a default.
2. **Record DLP commencement and end dates** as milestone entries in the project programme (`06-programme/`), using `register-row-draft` for the action or milestone row.
3. **Transfer open defects** from `07-construction/11-defects/` to `09-handover-dlp/` at PC. Non-critical deferred defects carry over as `in-rectification` rows.
4. **Set defects review trigger** at 80% of the DLP period — the project lead reviews open defects and issues written notices before DLP expiry. Flag this milestone date.
5. **Role-aware obligations reminder:**
   - `user_role: owner-builder` → load `../../01-seed/defects-and-dlp-guide.md §4.1` for buyer warranty obligations on future sale.
   - `user_role: builder` → load `../../01-seed/defects-and-dlp-guide.md §4.2` for HOW claim mechanics and statutory warranty obligations.

### Step 6 — Assemble handover pack

Invoke `../atomic/markdown-draft-for-review.md` with:

- **Target folder** — `09-handover-dlp/`;
- **Target filename** — `pc-checklist.md` (for the first PC; `pc-checklist-v<NN>.md` if re-running);
- **Asserted voice** — `contractual` (handover documents are contractual instruments — the PC certificate and final claim are binding);
- **Seed list consulted** — the seeds loaded at Step 1;
- **Evidence references** — the artefacts found at Step 2 that underpin the checklist.

#### Required sections in the PC checklist / handover pack markdown

The draft must contain at least these sections (in order):

1. **Project header** — project slug, client, site, archetype, user_role, state; PC checklist version; date; author; status (draft → reviewed → issued).
2. **PC certificate details** — date of PC, certifier or superintendent name, DLP commencement date, DLP end date, DLP review trigger date (80% of period).
3. **Checklist status table** — all 21 items with status populated from the evidence sweep.
4. **Held items** — any item with `✗ hold` listed with reason and required action.
5. **Defects schedule** — open defects from the defects walk, cross-referenced to the defects register in `07-construction/11-defects/`. Non-critical deferred items listed with agreed rectification dates.
6. **BASIX compliance confirmation** — BASIX final certificate reference number and date. If not yet obtained, note as a held item.
7. **HOW / HBCF certificate details** — certificate number, insurer, coverage period, handover date, owner acknowledgement.
8. **Final claim reference** — claim number, amount, date submitted, payment due date per contract.
9. **Handover pack receipt** — owner acknowledgement that O&M manuals, warranties, keys, and access devices have been received (date, owner signature or email confirmation reference).
10. **DLP tracking milestones** — DLP commencement, DLP end date, 80% review trigger date.
11. **Assumptions and open items** — any item still pending or assumed; explicit §evidence-discipline labels.

#### Voice register

`contractual` per the `09-handover-dlp/` voice assignment. Formal Australian English. ISO short-form dates in tables. Long-form dates in prose. No contractions.

### Step 7 — Surface gaps and escalations

Surface explicitly to the user:

- **BASIX final certificate not obtained** → **OC cannot issue. This is a critical hold.** Do not call PC without this certificate. Surface immediately and do not suppress.
- **HOW certificate not on file** → hold. OC certifier will not issue OC without evidence of HOW cover. Flag to owner and builder immediately.
- **Critical defects open at PC call** → the builder must not be released to PC until critical defects are resolved. Surface each open critical defect by Df-seq and required action.
- **Consent conditions outstanding** → OC application will be refused. Identify each outstanding condition by CC-seq and responsible party.
- **Final claim released before PC certificate issued** → flag as a contractual sequence breach. The final claim should not be released until the PC certificate is issued per the contract mechanism.
- **DLP end date not recorded** → flag as an action for the PM. Missing DLP end date means defect notices may be issued late, losing contractual rights.
- **DLP review at 80% of period not calendared** → flag as a programme action.
- For `user_role: owner-builder` — if the project is a new dwelling and the owner may sell within 7 years and 6 months, surface the owner-builder warranty disclosure obligation (per `../../01-seed/defects-and-dlp-guide.md §4.1`).

State-specific escalations:
- Non-NSW projects: flag that BASIX final certificate does not apply; confirm the applicable energy compliance evidence with the certifier.
- VIC projects: confirm DBI certificate (not HOW/HBCF) is on file; confirm DLP period in the VIC contract.
- QLD projects: confirm QBCC Home Warranty Insurance certificate is on file.

Escalation routing follows the role overlay loaded at Step 1 and `../../00-doctrine/doctrine.md §escalation-triggers`:
- **Owner-builder** — escalations to the self-flag log in `08-meetings-reporting/`.
- **Architect-PM** — escalations route to the owner via a `§owner-communication`-shaped summary.
- **Builder** — contractual escalations route via `07-construction/08-rfi-notices/` for the written record.
- **D&C** — as builder.

Route each escalation through `escalation-note-system.md` and report the trigger, route and recommended action in the return summary.

### Step 8 — Return summary

Return a short summary to the user:

- mode used (pc-checklist / dlp-review / advice-only);
- seeds loaded and recorded in `seed_consulted:` frontmatter;
- artefacts found by the sweep (relevance-ranked);
- PC checklist status — count of items complete, pending, and held;
- held items requiring immediate action;
- handover pack produced (path);
- defects register status — rows opened, rows transferred to `09-handover-dlp/`;
- DLP milestone dates recorded;
- gaps remaining (actions opened);
- escalations surfaced.

The user reviews the handover pack, resolves held items (or directs the agent to do so), and either signs off the PC checklist as `status: reviewed` or returns for iteration.

## Rule

This skill is the **canonical entry point** for residential PC and handover work in SiteWise. Other paths (ad-hoc PC checklists, manual register entries) are valid but lose the discipline this skill enforces: §2 gate at the boundary, §seed-consultation-discipline via `seed-targeted-read`, §evidence-discipline via `evidence-sweep` and the Fact / Assumption / Judgement / Recommendation labels, §register-discipline via `register-row-draft` for every defect row, §5 output discipline via `markdown-draft-for-review`, and the markdown-first / approved-source discipline.

This skill **does not certify PC, issue the OC, or sign off the final claim**. Those are human contractual acts. The skill produces the checklist and handover pack for the project lead's review and action. The agent does not flip its own drafts to `status: reviewed`.

This skill **does not suppress the BASIX final certificate hold point**. If the BASIX final certificate is not on file, the skill flags it and does not proceed to mark the OC application item as complete — regardless of user instruction to the contrary. The certifier cannot issue the OC without this certificate, and proceeding on a false positive will block settlement or occupation.

This skill **does not release the final claim on the agent's authority**. It documents that the conditions for release have been met (or flags those that have not) and presents this to the project lead for their decision.

This skill **does not create or modify the HOW/HBCF certificate**. It confirms the certificate is on file and hands over the document to the owner; it does not assess insurance coverage adequacy.

This skill respects `../../AGENTS.md §11` active-project boundary — it operates only within the active project folder. Deliverables written at Step 6 must sit within the active project folder.

## Skill skeleton inheritance

This skill inherits the slice-06+ skeleton documented in `contract-setup-system.md §"Skill skeleton — for slices 06+ to inherit"`:

1. **Pre-flight: §2 declaration gate** (Step 0 above).
2. **Step 1: `seed-targeted-read`** with task subject.
3. **Step 2: `evidence-sweep`** with task subject.
4. **Steps 3 to 6: content-specific atomics and drafting** — mode confirmation, checklist execution, DLP tracking setup, handover pack assembly.
5. **Step 7: surface gaps and escalations** explicitly.
6. **Step 8: return summary** — checklist status, defects, milestones, gaps, escalations.

This skill is the final system skill in the construction and handover lifecycle. It consumes the cost plan (final claim baseline) from `cost-plan-system`, the variation register (variation close-out) from `variation-management-system`, and the programme milestones (PC date) from `master-programme` and related programme skills. It opens the DLP tracking register that subsequent `dlp-review` invocations will maintain.

## See also

- `../../AGENTS.md §1` (authority stack), `§2` (declaration gate), `§3` (seed loading rules), `§5` (output discipline), `§6` (voice register — `09-handover-dlp/` is contractual), `§8` (state callouts), `§9` (skill invocation), `§11` (active-project boundary)
- `../../00-doctrine/doctrine.md §seed-consultation-discipline`, `§evidence-discipline`, `§register-discipline`, `§decision-discipline`, `§escalation-triggers`, `§voice-and-style`, `§owner-communication`
- `../../01-seed/defects-and-dlp-guide.md` — residential defects catalogue, DLP mechanics, role-aware warranty obligations, defect tracking schema (required seed for this skill)
- `../../01-seed/sustainability-energy-guide.md §5` — BASIX final certificate hold point workflow (required seed for this skill)
- `../../01-seed/contract-administration-guide.md` — final claim mechanism, PC definition, defect notice clause references
- `../../01-seed/program-scheduling-guide.md` — PC and DLP as programme milestones, conditional load
- `../../01-seed/cost-management-principles.md` — final claim, PC sum reconciliation, contingency close-out, conditional load
- `../../01-seed/new-dwelling-guide.md` (or other Tier 2 archetype seed per `archetype:`) — archetype-shaped PC and handover drivers
- `../../01-seed/role-builder.md` (or other Tier 3 role overlay per `user_role:`) — role-divergent handover and warranty responsibilities
- `../atomic/seed-targeted-read.md` — loaded at Step 1
- `../atomic/evidence-sweep.md` — loaded at Step 2
- `../atomic/markdown-draft-for-review.md` — used at Step 6
- `../atomic/register-row-draft.md` — used at Step 4 (defect rows) and Step 5 (DLP milestone rows)
- `contract-setup-system.md` — first SiteWise system skill and skeleton source
- `cost-plan-system.md` — second SiteWise system skill; this skill consumes the final cost plan it produces
- (Slice 06) `progress-claim-assessment-system.md`, `variation-management-system.md` — produce the variation close-out and PC reconciliation that this skill's final claim draws on
