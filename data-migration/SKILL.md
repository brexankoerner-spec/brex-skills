---
name: data-migration
description: Run a customer's data migration into Podium — anywhere from a single entity re-upload/retry through a full end-to-end migration. Full pipeline scrapes raw exports from the source FSM (HouseCall Pro, ServiceTitan, Jobber, etc.), cleans/transforms them into the Podium Migration Standard CSV schema, and uploads everything into Lighthouse's "FSM Data Transformer" wizard via Claude in Chrome browser automation. Use this whenever the user asks for a "full migration," "start-to-finish migration," "scrape and clean and upload X," hands you a scraper package to run and turn into an upload, or wants the whole pipeline rather than a single phase — and equally whenever the user asks to "re-upload"/"upload" customer data into Lighthouse/Podium for ANY entity (contacts, job history, invoices, estimates, pricebook materials/services, memberships/members, equipment, etc.), fix/retry a failed data migration entity, triage import error reports, or work through the Upload → Mapping → Preview → Transform → Review wizard on a customer's Data Migration tab, with or without a scrape/clean pass first.
---

# Data Migration (scrape → clean → upload)

The pipeline for moving one customer's data out of their old FSM and into
Podium — everything from a single entity re-upload/retry through a full
end-to-end migration. Four phases when running the whole pipeline, always
in this order (a standalone re-upload/retry request only needs Phase 3,
working from CSVs already in hand — Phase 1/2 aren't required for that):

1. **Scrape** — run the customer's exporter tool to pull raw data out of
   the source FSM.
2. **Clean** — transform the raw export into the Podium Migration Standard
   CSV schema, splitting out anything that can't be safely imported.
3. **Upload** — push the cleaned CSVs into Lighthouse's **FSM Data
   Transformer** wizard (Upload → Mapping → Preview → Transform → Review),
   including failure triage and retry logic. This is also the entry point
   for a standalone "re-upload"/"upload"/"retry this entity"/"triage this
   error report" request for any entity — contacts, job history, invoices,
   estimates, pricebook, memberships/members, equipment, etc. — driven
   entirely through `mcp__claude-in-chrome__*` browser automation (there is
   no API).
4. **Wrap-up** — once every entity in the work list is uploaded (or
   explicitly skipped/deferred with the user's sign-off), produce a
   failure-reasons breakdown.

**⚠️ Completeness principle: everything that gets scraped has to end up in
the customer's Podium account — the CSV wizard is one route there, not the
only one.** "Full migration" doesn't mean "every entity the FSM Data
Transformer wizard happens to have a Target Tables checkbox for" — it means
every entity actually present in the source data. Two entity types are not
CSV-wizard-uploadable at all and must not be silently dropped just because
Phase 3's wizard has no slot for them:
- **Users/Technicians** — the source FSM's staff roster has to be created
  as Podium users and designated as Technicians directly in the customer's
  live account (via Mock), not through the wizard. See "Prerequisite: get
  Business Units, Job Types, and Technicians into Podium before mapping" in
  Phase 3 below for the full mechanics. **This must happen before Job
  History is uploaded** — see that section and "Upload order matters"
  below; it is a hard ordering requirement, not just a data-quality nicety,
  since there is no batch way to attach technicians to already-imported
  jobs after the fact.
- **Estimate Templates** (and **Membership Plans**) — these checklist rows
  have no Target Tables entry in the wizard at all. Route them through
  Lighthouse's **"Set Up ___ with Operator"** action on that entity's
  checklist row (the only documented path for Estimate Templates), or, for
  Membership Plans, either that same Operator flow or build the plan
  catalog by hand in the customer's account via Mock. See "Known
  entity-specific quirks" → Membership Plan Mapping in Phase 3 below for
  the full walkthrough of both paths. Treat both as standing, required
  steps of every full migration, not optional add-ons.

If anything else scraped turns out to have no wizard support either, the
same rule applies: check the checklist row's Actions dropdown for a
"Set Up ___ with Operator" (or equivalent) entry first, and if there isn't
one, mock in as the customer and build it directly in their account rather
than leaving it out of the migration. Don't treat "the wizard doesn't
support this" as a reason to skip an entity — only the standing exclusions
below (reviewed/N/A rows, Attachments) are allowed to be skipped by
default.

**Standing exclusions for a "full migration" (always, unless the user says
otherwise):**
- Any entity already marked **`REVIEWED`** or **`N/A`** on the customer's
  Lighthouse Data Migration checklist — these are finalized and must not be
  re-touched. See Phase 3's "Pre-flight" section below.
- **Attachments** — excluded from the standard scrape/clean/FSM-wizard
  pipeline as a standing policy for this shop (matches the existing
  "rescrape without attachments" convention), and left as `NOT STARTED`
  on the checklist unless the user explicitly asks for job attachments
  to be migrated. When they do ask, it's a **separate pipeline** from
  everything else in this file — see "Phase 3b — Job Attachments" below.
  It does not go through Phase 1/2/3 (no CSV cleaning, no FSM Data
  Transformer wizard) — a different scraper and a different upload tool.

**Default: pause on anything unspecified.** During the Lighthouse upload
phase especially — but really at any phase — if you hit a screen,
behavior, or decision point the user hasn't already told you how to
handle (an unfamiliar wizard step, an untested code path like the
multi-entity "bulk mode" Target Tables select, an ambiguous failure),
**stop and ask the user to explain that part before continuing**, rather
than guessing. This is a live production system; the cost of asking is
low and the cost of guessing wrong is not.

**⚠️ Skill-wide judgment-call rule (this is the umbrella the Phase-2
"judgment-call gate" and every per-case "ask/flag/confirm" instruction
elsewhere in this file are instances of — read this once, apply it
everywhere, not just where it's repeated):** every judgment call anywhere
in this skill falls into one of two categories, and they're handled
differently:

- **Destructive or guessing fixes — always confirm with the user before
  applying, every single time, even when the pattern is well-known and
  documented.** This covers anything that overwrites, discards, blanks,
  or reclassifies real customer data based on a heuristic that could be
  wrong — e.g. picking a "canonical" contact row and blanking an
  identifier elsewhere (Phase 2, contact dedup), rebuilding a job's start
  date from a heuristic (Phase 2, JOBS multi-day question), classifying a
  failed row as non-importable/needing manual Rolodex cleanup based on
  inference rather than a deterministic signal (Phase 3, "pre-existing in
  Podium" identifier conflicts), or anything you notice that doesn't
  cleanly fit a documented rule (see the "Known FSM data quirks catalog"
  at the end of Phase 2). "We've seen this exact quirk before" is a
  reason to have the explanation and fix *ready to offer*, not a reason
  to skip asking — being familiar with a quirk doesn't make guessing
  right this time free of risk.
- **Settled, non-destructive interpretive conventions — already confirmed
  with the user once, applied as a standing default without re-asking.**
  This covers vocabulary/interpretation decisions that don't lose or
  overwrite any data, only decide how to label or leave something —
  e.g. the Estimate/Invoice status-mapping "map by what it insinuates"
  rule, leaving a semicolon-combined technician string unassigned, leaving
  a job-type with no Podium equivalent unmapped, or treating an
  email-triggered export that never arrives as a likely FSM-side bug and
  continuing without it (see the "Known scraper quirks" note in Phase 1).
  These stay standing defaults on purpose — re-litigating an
  already-vetted, harmless labeling convention every migration would be
  pure friction with no safety benefit. If you're ever unsure which
  category something falls into, default to treating it as the first
  (destructive/guessing) kind and ask.

## Milestone checkpoints

Whenever you complete a major milestone, or sub-task, STOP immediately. Do
not proceed to the next step. Instead, output the following message
exactly: "TASK COMPLETE: Please run /compact to clear the context before
we continue."

## Phase 0 — Locate the scraper

The customer's working directory (e.g. `<Customer>/<date> upload/`) starts
out containing **just the scraper package** — either an already-unzipped
folder or a `.zip` (e.g. `HouseCall Pro 08_13.zip` →
`HouseCallPro-Exporter-updated/`). If it's zipped, unzip it in place first:

```
unzip -o "<Name>.zip" -d .
```

**Every scraper package ships its own `README.md`** (sometimes with a
second, deeper `.md` alongside it) — that file is the authoritative source
for setup, credentials, run order, and output location **for that specific
FSM**. This skill deliberately does not hardcode any one FSM's exact
commands, because different customers come from different source systems
(HouseCall Pro, ServiceTitan, Jobber, ...) each with their own exporter
tool. **Always read the package's own README before running anything.**

Shape learned so far from the HouseCall Pro exporter (illustrative of the
*pattern* other exporters likely follow — verify against the real README
every time, don't assume):
- `npm install` (Node + Puppeteer against the system Chrome, plus a
  spreadsheet library like exceljs).
- Copy the `*.env.example` → `*.env` and fill in credentials — **ask the
  user for these, never invent or guess them.**
- First run is interactive/headed (`HEADLESS=false`) to complete login +
  MFA; the session persists to a session dir so later runs can go headless.
- A handful of **per-entity scripts** run in sequence (contacts, jobs,
  invoices/estimates, pricebook, equipment, memberships, ...), each writing
  its own workbook — some entities may only be available via an
  email-triggered export rather than a direct API pull; the README will
  say which.
- A final **merge script** collapses the individual workbooks into one
  combined workbook per customer.
- Output is normally **`.xlsx`**, not CSV yet — that's Phase 2's job to
  convert.

## Phase 1 — Run the scrape

- Follow the README's documented run order **exactly** — later scripts
  can depend on earlier ones having completed (e.g. a contacts pull
  before a jobs pull, so jobs can join against contact IDs), mirroring
  the same foreign-key ordering issue Lighthouse itself has on upload.
- Long-running exports (e.g. buffering every invoice preview in memory)
  may need to run detached/under `caffeinate` per the README — follow
  its guidance rather than backgrounding it in some ad hoc way.
- Move/organize the raw output into `raw/` in the customer's working
  directory (see folder conventions below) if the scraper drops files
  somewhere else (e.g. `~/Downloads`), so Phase 2 has one predictable
  input location: `raw/<Customer Name>_<entity>.csv` (or `.xlsx` —
  convert/export sheets to per-entity CSVs before cleaning if the
  scraper's output is a single multi-tab workbook).

### Known scraper quirks (learned from the HouseCall Pro exporter — verify whether analogous issues exist for other FSM exporters, don't assume they don't)

- **`.env` isn't self-loaded by every script.** The main entrypoint
  (`housecallpro-exporter.mjs`) parses its own `.env` file into
  `process.env` at startup, but the smaller single-purpose companion
  scripts (contacts/jobs/equipment/memberships, estimate templates,
  checklists, ...) read `process.env` directly with **no fallback** —
  if you just run `node hcp-contacts-joined.mjs` without exporting the
  `.env` vars into the shell first, `HOUSECALLPRO_SESSION_DIR` comes
  through `undefined`, Puppeteer launches a **fresh, unauthenticated**
  browser profile instead of the persisted logged-in session, and the
  script fails opaquely (e.g. `TypeError: first.data is not iterable`
  from an API call that silently got back an unauthenticated response
  instead of JSON — not an auth error, so it's easy to misdiagnose as
  something else). **Fix:** export the `.env` into the shell before
  running any companion script: `set -a && source housecallpro.env &&
  set +a && node <script>.mjs`. Check whether an equivalent gap exists
  in other FSM exporters' companion scripts before assuming this one
  case was a one-off.
- **Quote `.env` values that contain spaces or shell-special
  characters** (e.g. `HOUSECALLPRO_CUSTOMER_NAME="Apex Residential"`,
  `HOUSECALLPRO_PASSWORD="Some!Password"`) — needed for `source` to
  parse the file correctly when exporting it into the shell per the
  point above. The main exporter's own manual line-parser tolerates
  unquoted values with spaces, but `source` in a shell does not.
- **A bare `Navigating frame was detached` error from a pricebook (or
  similar settings-page) export is often just a transient Puppeteer/page
  race**, not a real config problem — retry once before investigating
  further.
- **If an email-triggered export (e.g. Pricebook Services/Materials)
  never produces the expected email** after triggering it (check the
  inbox the export was addressed to, including past historical runs to
  see if it *ever* arrived) — **assume the source FSM has a bug or the
  account genuinely has no data for that category, and continue the
  migration without it.** Don't keep re-triggering indefinitely or block
  the rest of the pipeline on it; note the gap in the final report
  instead. (Confirmed as the right call by the user rather than treating
  it as a blocking unknown — see the "Pre-flight" pause-and-ask default
  below, which this is an explicit, standing exception to for this
  specific failure mode.) Likewise, an email export that *does* arrive
  but is header-only/empty (e.g. a Materials pricebook CSV with 0 data
  rows) means the source account has no real data in that category —
  produce an empty/absent `cleaned-data/<entity>.csv` and say so in the
  report rather than treating it as an error.

## Phase 2 — Clean → `cleaned-data/`

You are cleaning raw data exports from the source FSM into clean,
import-ready CSV files matching the **Podium Migration Standard** target
schema.

**🎯 Start from `scripts/clean_migration_data.py` (in this skill's folder)
instead of writing a cleaning script from scratch.** It's the reusable core
extracted from two real, working migration scripts (Apex Residential /
HouseCall Pro and MLD Services / Jobber), with every FSM-agnostic rule in
this section already implemented as a function: global formatting, junk-phone
detection, the contact dedup/merge framework (union-find, property-management
anti-over-merge, the household phone/email primary-pairing safety fix, the
post-merge identifier-conflict fix), required-field splitting helpers, job
date-building (both the "prefer explicit start" default and the multi-day
variant), money conversion (including the line_items_json dollar-to-cents
fix), the exact Podium Migration Standard CSV headers for every entity, and
the "new since &lt;date&gt;" delta helpers. Copy it into the customer's working
directory as `clean.py` and only fill in the `# CUSTOMIZE:` marked spots —
the raw source shape/location, this FSM's actual column names, and any
FSM-specific quirks — rather than re-deriving the mechanics every migration.
The template's own docstring and inline comments cite exactly which
confirmed bugs (documented below) are already fixed vs. which judgment calls
still need a human read of the real data; read those before assuming a
default is safe to skip.

### Deliverables

Produce these files (only for entity types actually present in the source
data) and place **all of them in a folder called `cleaned-data/`**:

**Import-ready files:**
`customers.csv`, `jobs.csv`, `invoices.csv`, `estimates.csv`,
`pricebook-services.csv`, `pricebook-materials.csv`, `equipment.csv`,
`members.csv`

**Non-importable exception files** (same column schema as their
counterpart above, no extra `reason` column, rows preserved untouched for
manual review):
`customers-non-importable.csv`, `jobs-non-importable.csv`,
`invoices-non-importable.csv`, `estimates-non-importable.csv`,
`pricebook-services-non-importable.csv`,
`pricebook-materials-non-importable.csv`,
`equipment-non-importable.csv`, `members-non-importable.csv`

### Rules & validation workflow

**⚠️ Judgment-call gate for this phase** — this is the Phase 2 instance of
the **skill-wide judgment-call rule** at the top of this file: read that
first if you haven't. In short, the fixes in this section split into
destructive/guessing ones that need fresh confirmation every time (most
notably the property-management merge-blocking + identifier-conflict fix
in rule 3, and the HouseCall-Pro multi-day job-date heuristic in the JOBS
schema below — **detect the pattern in the actual data first, explain it
to the user in plain terms with concrete examples, and get explicit
confirmation before applying**) versus settled conventions that don't
need re-asking. This generalizes beyond those two named cases: whenever
you notice obviously dirty data in ANY entity (multi-day/multi-week job
spans, suspiciously repeated identical dates/times across many job/
estimate/invoice records, or anything else that doesn't cleanly fit a
documented pattern), check the **"Known FSM data quirks catalog"** at the
end of this phase before deciding how to handle it — see that section for
the full consult-and-confirm workflow, including what to do when the
pattern matches a quirk already known for a *different* FSM versus when
it's genuinely novel.

**1. Pre-execution inspection.** Inspect every source file: list all sheet
names, column headers, row counts, and sample records. Verify exact column
names — if an instruction below references a column that doesn't exist in
the actual source, **stop, report it, and propose the closest sensible
mapping before proceeding.** Never drop rows silently: every source row
must end up in either a main import file or its non-importable exception
file.

**2. Global formatting rules.**
- **Date & time:** ISO 8601, and **must include whatever timezone
  indicator the source data actually has** — `2018-11-02T19:41:03Z` for
  UTC, `2018-11-02T19:41:03-05:00` for an offset. Don't force `Z` onto a
  source that specifies a different offset. Date-only source values default
  to `YYYY-MM-DD`. Apply consistently across every date/time column in
  every sheet.
- **Spreadsheet-escaped values:** convert `="123"` → `123`.

**3. Contact deduplication & merging (Customers, Members, etc.), before
writing output:**
- **Junk/shared phone blacklist:** drop obvious junk/dummy/shared numbers
  (toll-free lines, `555-555-5555`-style test numbers, the company's own
  office line) *before* merging. If one number is smeared across several
  unrelated names/addresses, blank the phone field on those rows rather
  than letting it drive a false merge — keep the contact record itself.
- **Match strategy:** normalized phone (10 digits, post-blacklist),
  lowercased email, or exact full name + address.
- **Anti-over-merging rule (property management):** do **not** merge a
  group if it would end up with more than 2 distinct phone numbers OR more
  than 2 distinct emails — that's a signal of a property-management/
  commercial account, not a real duplicate-person match. Merging those
  buries matching criteria in notes and breaks downstream job/invoice
  matching. Leave them as separate, unmerged rows.
  - **The phone/email cap alone isn't sufficient — also check for a
    property-manager/landlord/realtor `job_title` field, and check the
    *combined* address count across the whole candidate merge group (not
    just each individual source record).** Found in practice: a contact
    tagged `job_title: "Property manager"` with 20 addresses on one
    source record is an obvious per-record signal, but several other real
    property managers only showed up as many *separate* source records
    (different customer IDs, ≤2 addresses each) that all shared one
    phone/email — no single record hit an address-count threshold, only
    the union across the merge candidates did (one email reached 28
    candidate rows / 25 distinct addresses this way). Compute the union
    of addresses across the whole candidate group and block the merge if
    it's large (≥5 is what worked here), in addition to per-record
    signals.
  - **⚠️ Blocking the merge is not enough on its own — you must also
    break the shared identifier across the split-apart rows, or the
    problem just resurfaces at the Podium import layer.** If you split a
    blocked group back into one row per source record without touching
    anything else, every row still carries the *same* shared email (or
    phone) with a *different* counterpart phone (or email) per row —
    Podium's own contact-matching then fails each of those rows with
    `"identifier conflict: phone and email resolve to different Rolodex
    contacts"` (see Phase 3's "Triaging failures" failure-reason notes
    below), which is arguably worse than the original over-merge since it
    now surfaces at upload time across many rows instead of being visible
    in one cleaning-time decision. **Fix:** after blocking a merge, still
    dedupe the shared identifier itself — for every email (or phone)
    appearing on 2+ of the split rows with genuinely different
    counterpart values, keep it on exactly one canonical row (e.g. the
    one with the most complete `contact_notes`) and blank it on the rest,
    so every row has an unambiguous identifier. A row that loses its only
    identifier this way (blank phone *and* now-blanked email) correctly
    falls out to `-non-importable.csv` per the required-field rule below
    — that's expected, not a bug.
    **⚠️ This fix picks a "canonical" row by a heuristic (most complete
    `contact_notes`) — that's a guess about which record is the "real"
    one, not a certainty, so it goes through the judgment-call gate
    above: don't apply it silently.** Run it as a **single batch
    confirmation per migration**, not per group — once every blocked
    group has been found, show the user: how many groups were blocked,
    how many total rows are affected, one or two concrete real examples
    (the shared identifier, the canonical row picked and why, which
    other rows would get that identifier blanked, and any rows that
    would consequently drop to non-importable for having no identifier
    left), and a plain-language explanation of the mechanism itself.
    Get one explicit go-ahead before writing the fix to every blocked
    group's output rows. **If the user declines, don't fall back to
    guessing a different default** — ask them directly how they'd like
    the blocked groups' shared identifiers handled instead (e.g.
    manually specify the canonical contact per group, leave the
    duplicated identifiers as-is and accept they may resurface as Phase
    3 identifier-conflict failures to triage individually, or route the
    non-canonical rows straight to `-non-importable.csv` for manual
    follow-up). The `scripts/clean_migration_data.py` template's
    `group_should_block_merge` and `fix_shared_identifier_conflicts`
    functions implement the mechanics; they're written to be called only
    after this confirmation, not automatically as part of the pipeline.
- **Merge mechanics:** combine duplicates into one master record; fill
  nulls in the master from whichever duplicate has the value; store the
  primary phone/email in the main fields and fold secondary unique contact
  info into `contact_notes`; merge + dedupe tags (comma or `|` separated);
  append notes together in order; **re-link every associated Job, Invoice,
  Estimate, Equipment, and Membership row to the merged master record.**
  - **⚠️ "First phone + first email" as the primary pair is not safe when
    a single source contact record represents a household of 2+ real
    people (e.g. a couple), because the source's `phones`/`emails` arrays
    are not guaranteed to be index-aligned per-person.** Confirmed in
    practice (Jobber): a client record named "Meagan Rose" carried two
    phones and two emails — `phones = [Meagan's, Ethan's]` but
    `emails = [Ethan's, Meagan's]` (reversed order relative to the
    phones). Picking phone[0] + email[0] as "the" primary pair produced a
    row with Meagan's phone cross-wired to Ethan's email — two different
    real people's identifiers stitched onto one row. This doesn't get
    caught by the phone/email-count anti-over-merge threshold (only 2
    phones / 2 emails / 1 address here, well under the ≥5-address or
    >2-identifier trip wires) because it isn't an over-merge of *multiple
    source rows* — it's a bad primary-pairing choice *within a single*
    source row. It only surfaces later, at Lighthouse upload time, as an
    `identifier conflict: phone and email resolve to different Rolodex
    contacts` error (if Podium's Rolodex already has the two people as
    separate contacts from an earlier upload) — see Phase 3's "Triaging
    failures" section, "third source" identifier-conflict case, for the
    fix once it's already been uploaded wrong. **To avoid it at cleaning
    time:** when a source record has 2+ phones AND 2+ emails, don't
    blindly zip phone[0] with email[0] as primary — that pairing is only
    trustworthy if the source data actually correlates them per-person
    (verify, don't assume). If there's no reliable way to tell which
    phone belongs with which email from the source alone, prefer keeping
    just the record's single most load-bearing identifier as primary
    (e.g. the one matching `client.phone`/`client.email` singular fields
    if the source exposes those separately from the plural arrays) and
    fold every other phone/email into `contact_notes` as unpaired
    extras, rather than asserting a specific cross-pairing the data
    doesn't actually support.

**4. Required-field / non-importable splitting.** A row with all its
required fields non-blank goes to the main CSV. A row missing **any**
required field goes to the matching `-non-importable.csv`, data preserved
as-is for manual review.

### Schema definitions

**CUSTOMERS** (`customers.csv` / `customers-non-importable.csv`)
- Required: `first_name`, plus at least one of phone/email.
- Headers (exact order): `first_name, last_name, phone, email,
  street_address, unit, city, state, postal_code, country, tags,
  contact_notes, property_relation, property_type, quickbooks_customer_id`
- Consolidate Mobile/Home/Work phone into one `phone` (priority Mobile →
  Home → Work). Combine address components into the standard fields; if a
  customer has multiple properties, concatenate the extras into
  `contact_notes`. Rows with no real `first_name` (e.g. only an address
  string like "160 Meadow Park" and no name anywhere) OR missing both
  phone and email → non-importable.

**JOBS** (`jobs.csv` / `jobs-non-importable.csv`)
- **⚠️ Never dedupe or merge job rows.** Unlike Customers/Members, every
  source `job_id` gets exactly one output row, always — even if several
  jobs share the same customer, date, address, or look like near-duplicates.
  Two jobs are never "the same job" just because they resemble each other;
  only an actual identical `job_id` is the same job. Confirmed: every
  `cleaned-data/jobs.csv` produced so far has unique==total job_ids (no
  collisions), so no dedup logic should ever be introduced into this step.
- Required: `job_id`, `customer_name`, `job_title`, `job_start_date`.
- Headers (exact order): `job_id, customer_name, customer_phone,
  customer_email, job_title, technician, job_start_date, job_end_date,
  job_type, status, notes, address_street, address_unit, address_city,
  address_state, address_postal_code`
- Consolidate separate date/time source columns into unified
  `job_start_date`/`job_end_date`. Accepted formats if not following the
  global ISO 8601 rule: `2024-06-15T10:00:00` (ISO, with Z/offset/ms),
  `01/15/2025, 10:30 AM`, `2025-01-15 14:30`, `2025-01-15`. Past jobs:
  prefer actual start/end dates. Future jobs: use scheduled dates. Job has
  a completed date but no start date → set `job_start_date` to 1 hour
  before completion.
  **⚠️ Process for the multi-day question — goes through the
  judgment-call gate above, don't auto-apply either direction:** the
  **default is to import `job_start_date`/`job_end_date` as given** —
  i.e. prefer the source's own explicit start field over any end-derived
  override (this is `scripts/clean_migration_data.py`'s
  `build_job_start_end`, and it's the behavior confirmed correct for
  Jobber — see the superseded-finding writeup below).
  - **If the source is HouseCall Pro specifically:** first check whether
    the multi-day pattern actually shows up in this account's data (jobs
    where start/end differ by more than ~24h — the same threshold
    `build_job_start_end_multiday_variant` uses). If it does, this is a
    **known, previously-confirmed HouseCall Pro quirk** (see the "Known
    FSM data quirks catalog" at the end of this phase) — flag it to the
    user with the count found and a couple of concrete examples, explain
    that the fix rebuilds `job_start_date` as end-minus-1-hour for those
    rows, and **offer to apply it**. Only apply
    `build_job_start_end_multiday_variant` if they say yes; otherwise
    leave the dates as-is per the default above. Do this every migration
    for HouseCall Pro — "it's a known quirk" doesn't mean skip asking,
    it means you already have the explanation and the fix ready to offer.
  - **If the source is any other FSM and you see the same kind of
    symptom** (start/end spans that look implausibly long, or any other
    obviously dirty date pattern — e.g. many jobs sharing one suspicious
    identical timestamp), **consult the "Known FSM data quirks catalog"
    first.** If a similar or identical quirk is already documented for a
    *different* FSM, tell the user what you found here, cite the
    precedent (which FSM, what the root cause turned out to be, what fix
    was used there), and offer an analogous fix — verified against
    *this* FSM's actual raw data before applying, not blindly ported,
    since the same symptom can have a different root cause on a
    different system (see the Jobber case below, where the HouseCall Pro
    fix looked plausible but was actually wrong). **If nothing similar is
    documented anywhere, treat it as a novel quirk: you MUST flag it to
    the user with your suggested fix option(s) and ask how they'd like to
    proceed** — don't silently pick a default for an undocumented
    pattern. Either way, once resolved, add what you learned as a new
    entry in the catalog so the next migration on that FSM (or a
    similar-symptom FSM) benefits from it.

  The rest of this note is the historical record of how the current
  default was arrived at — useful context for *why* "prefer explicit
  start" is the default, not a new rule on top of the process above.
  **Multi-day rule (HouseCall Pro-specific, offer-only per the process
  above):** if start/end span multiple days, the END date is the source
  of truth — set `job_start_date` to exactly 1 hour before the end
  date/time. This rule was derived from HouseCall Pro — it does not
  transfer to other FSMs by default. Confirmed broken as a blanket rule
  for **Jobber**: its
  `endAt` field on RECURRING/membership jobs (and even some ONE_OFF jobs)
  can hold a far-future sentinel value (multi-year spans seen in practice,
  e.g. a 2025 job with `endAt` in 2031) rather than a real visit end, so
  blindly taking "end minus 1 hour" corrupts `job_start_date` for a large
  fraction of the dataset (~60% of one Jobber account's jobs had
  start≠end dates, ~20% of those spanning 61 days to 10 years). **For
  Jobber specifically, apply a ~14-day cutoff**: if end is within 14 days
  of start, treat it as a real multi-day job and use end-1hr as the
  literal rule says; beyond 14 days, treat the end date as unreliable and
  keep the original start date/time instead.
  **⚠️ Superseded finding (2026-08-14): the 14-day cutoff is still not
  good enough for Jobber — prefer the explicit start field over any
  end-derived heuristic whenever the source exposes one.** Cross-checked
  a full account's `jobs.csv` against Jobber's own official "Job History"
  report export (Insights → Reports, has separate "Created date" /
  "Scheduled start date" / "Closed date" columns) and found ~2,228 of
  2,237 ONE_OFF jobs — the overwhelming majority, including gaps as short
  as 1 day — had their `job_start_date` silently set to the job's
  **Closed date** instead of its real **Scheduled start date**. A
  same-week gap between start and end is usually just "the visit got
  completed a few days after it was scheduled," not a genuine multi-day
  job, so even the 14-day cutoff misclassifies it. The raw Jobber
  scraper output actually carries the real scheduled start as its own
  field, separate from completion: `job_start_date` (date-only) +
  `start_time` are the true scheduled start, while `job_end_date` +
  `end_time` are the actual completion timestamp (which is where the
  sentinel-year bug above lives). **Rule for Jobber: build
  `job_start_date` directly from the raw scraper's `job_start_date` +
  `start_time` columns (or the official export's "Scheduled start date"
  if cross-referencing against it), not from any end-minus-offset
  heuristic — reserve the end-derived heuristic for FSMs that don't
  expose a separate real start field.** The "completed date but no
  start date → end minus 1 hour" fallback is separate and still applies
  as-is regardless of FSM (confirmed still correct for Jobber — it's how
  a small number of jobs with a bogus *negative* span, end before start,
  get fixed: those come from the scraper falling back to `createdAt` for
  a missing `startAt`, landing after the real completion time). **The
  same Jobber sentinel-date quirk also showed up in Memberships**, not
  just Jobs: a membership's `end_date`/`next_auto_renewal` (both derived
  from the source job's `endAt`) are bogus far-future values whenever
  `is_auto_renewal` is true (spans clustered right around whole-year
  boundaries — 365, 731, 1827, 2191, 3653 days — vs. exactly 1 day for
  every `is_auto_renewal=false` row, which is real). Fix: blank `end
  date`/`next auto renewal` outright when `is auto renewal?` is true
  rather than passing the sentinel through — an active recurring
  membership genuinely has no known end date. Check for this same pattern
  in any other date field derived from Jobber's `endAt` before trusting
  it. **Ambiguity rejection:** if a job has
  neither `customer_phone` nor `customer_email` and relies on
  `customer_name` alone, check the Customers dataset — if that name isn't
  unique there, the job can't be matched precisely → non-importable. Any
  row missing a required field → non-importable.
  **⚠️ Confirmed at upload time: name-only matching is unreliable even
  when the name IS unique — don't treat "unique in the Customers dataset"
  as a green light on its own.** Real outcome from one migration: 289
  jobs had blank `customer_phone`/`customer_email` and relied on
  `customer_name` alone; 105 matched fine, but 181 failed at Lighthouse
  upload with `"Customer could not be matched. Provide at least one of:
  customer_email, customer_phone."` — despite passing the
  uniqueness check at cleaning time. Root cause, found by cross-checking
  the failed jobs' `customer_name` values against `customers.csv`: most
  of those names **don't appear in either `customers.csv` or
  `customers-non-importable.csv` at all**, because they were **company
  contacts** (`is_company: yes` in the Jobber source) with the business
  name only in `company_name` and both `first_name`/`last_name` blank —
  and the Podium Migration Standard `CUSTOMERS` schema **has no
  `company_name` column**. Those contacts silently lose their only name
  on the way into `customers.csv`/`-non-importable.csv` (both first/last
  blank), while the JOBS sheet's `customer_name` still carries the real
  company name straight from the source, so the two files can never
  agree on a name to match by. **If you hit this, ask the customer/user
  whether company contacts should get `company_name` promoted into
  `first_name` as a fallback** (not done by default, since the schema
  doesn't call for it and it's a real judgment call) rather than quietly
  reclassifying them as importable — this is exactly the kind of
  ambiguity worth a pause, not a silent guess. Until that's resolved,
  treat any name-only job whose customer is a company contact as
  effectively non-importable, and don't be surprised if plain personal
  names fail too (the 181 failures weren't all companies — Podium's
  matcher may not attempt name-only matching at all in some cases despite
  the uniqueness check passing client-side; verify against real upload
  results rather than trusting the cleaning-time check alone).

**INVOICES** (`invoices.csv` / `invoices-non-importable.csv`)
- Required: `external_id`, `status`, `total_cents`.
- Headers (exact order): `external_id, status, job_id, customer_phone,
  customer_email, total_cents, subtotal_cents, tax_amount_cents,
  discount_amount_cents, issue_date, due_date, notes, line_items_json`
- **🚨 CRITICAL — `external_id` must be the real, human-readable invoice
  number, NOT whatever raw column happens to be named `external_id`.**
  Confirmed for Jobber: the raw scrape has **two different ID columns**
  for the same invoice — `external_id` (Jobber's internal API ID, a
  base64-ish string like `MTY3OTMyODM3` — wrong) and `invoice_number`
  (the actual short number printed on the invoice, e.g. `24567` — right).
  A same-shaped, identically-named column is not proof it's the correct
  value — **read the raw CSV's actual columns yourself and confirm which
  one is the number a human would recognize from the FSM's own UI**
  before wiring up the mapping; don't assume the raw column named
  `external_id` is automatically the target field named `external_id`.
  This was caught late, at the Lighthouse Preview screen, on a live
  upload — catch it here instead by checking the raw file first. Verify
  the chosen column is unique/non-blank across all rows before using it.
  Dollar values → integer cents.
  **🚨 CRITICAL — this applies to `line_items_json`'s nested
  `unit_price`/`unit_cost` too, not just the top-level `*_cents`
  columns.** The scraper emits these as dollar strings (e.g.
  `"unit_price": "$25.00"`), which Lighthouse's import rejects outright
  with `line_items.N.unit_price: must be a integer` / `...unit_cost:
  must be a integer` — **confirmed to fail 100% of rows** (4,236/4,236 on
  one account) when left unconverted, since every invoice/estimate has
  line items. Parse the JSON, convert every line item's `unit_price` and
  `unit_cost` from a dollar string to an **integer number of cents**
  (not a string — a JSON number), and re-serialize before writing
  `line_items_json`. Don't assume line-item money fields inherit the
  same dollars-vs-cents convention as sibling top-level columns — verify
  each nested numeric field's expected type/units independently, ideally
  by test-uploading a small batch before running the full file through
  Lighthouse.
  **⚠️ Blank/empty-string `unit_cost` needs an explicit fallback, not a
  pass-through.** A naive dollar-string-to-cents converter that only
  special-cases `None` will leave a genuinely blank source value (`""`)
  untouched — still a string, still rejected by the same `must be a
  integer` check, just less obviously (48 rows failed this way on one
  account, from line items where `unit_cost` was blank in the source
  because no internal cost was ever recorded for that item). Treat blank/
  missing `unit_cost` as **0 cents**, not as "leave it as-is" — an
  explicit zero is a valid integer and reflects "no known cost," which is
  the honest interpretation of a blank source value. Re-run the actual
  fix function against a known-blank sample and confirm the *output type*
  is `int`, not just that the code path was exercised, since this bug
  only breaks the empty-string case specifically. **Missing-link
  recovery:** an invoice
  needs at least one of `customer_phone`/`customer_email`/`job_id` to link
  to a customer. If both phone and email are missing, try recovering them
  from the Customers sheet by name match — **valid only if the name
  matches exactly one customer**; ambiguous name → recovery fails. Missing
  all three linking fields even after recovery, OR missing `external_id`/
  `status`/`total_cents` → non-importable.

**ESTIMATES** (`estimates.csv` / `estimates-non-importable.csv`)
- Required: `name`, `total_cents`, `subtotal_cents`.
- Headers (exact order): `name, external_estimate_id, customer_name,
  customer_email, customer_phone, job_id, total_cents, subtotal_cents,
  discount_amount_cents, discount_percentage, valid_until, created_at,
  notes, estimate_status, line_items_json`
- **🚨 Same critical ID bug as Invoices, confirmed here too:** raw
  `external_estimate_id` is Jobber's internal API ID (e.g.
  `NjMyMTEzNDU=`) — wrong. Raw `quote_number` is the real short estimate
  number (e.g. `656`) that a human recognizes — use **that** to build
  `estimates.csv`'s `external_estimate_id` column instead. See the
  identical Invoices note above for the general rule (check the raw
  columns yourself, don't trust a matching column name).
- **🚨 Same `line_items_json` integer-cents bug as Invoices applies here
  too** — see the Invoices note above; convert `unit_price`/`unit_cost`
  on every estimate line item from a dollar string to integer cents the
  same way, or every estimate upload fails the same way invoices did.
- `created_at`: use the source's actual `created_at` field if present;
  otherwise fall back to the estimate's general creation/issue date. Same
  missing-link recovery/rejection logic as Invoices (phone/email/job_id,
  name-uniqueness-gated recovery). Missing all three linking fields even
  after recovery, OR missing `name`/`total_cents`/`subtotal_cents` →
  non-importable.

**PRICEBOOK — SERVICES** (`pricebook-services.csv` /
`pricebook-services-non-importable.csv`)
- Required: `category`, `name`.
- Headers (exact order): `category, name, price, after_hours_price,
  description, taxable, task_code, industry, unit_of_measure, unit_cost,
  materials, duration, labor_rate, labor_duration, income_account,
  expense_account`
- **⚠️ `name` must be the human-readable name from the source system —
  never just the raw part number / SKU / item ID.** The Podium `name`
  column is what techs and customers see in the app; a bare identifier
  like `PT650001` or `est_ea7ee779...` is not a usable name. If the
  source export only carries an identifier in its "name" field, pull the
  real descriptive name from the source's own item description / display
  name / catalog title instead (e.g. `1.5 Ton Condenser - PT650001`, not
  `PT650001`), and keep the identifier in `task_code` (services) /
  `material_number` (materials). Confirmed the hard way on Apex
  Residential: ~354 condenser/heat-pump pricebook items were imported
  with the part number as the name and had to be renamed by hand in the
  product afterward — check the source's name field before cleaning and
  flag it to the user if it's identifier-only.
- Prices (`price`, `after_hours_price`, `unit_cost`, `labor_rate`) in
  **dollars** (`150.00`) — divide by 100 if the source has cents.

**PRICEBOOK — MATERIALS** (`pricebook-materials.csv` /
`pricebook-materials-non-importable.csv`)
- Required: `category`, `name`.
- Headers (exact order): `category, name, price, after_hours_price,
  description, taxable, task_code, industry, unit_of_measure, unit_cost,
  material_number, income_account, expense_account`
- **⚠️ `name` must be the human-readable name from the source system —
  never just the raw part number / SKU / item ID** (same rule as
  PRICEBOOK — SERVICES above; see that note for the full rationale and
  the Apex Residential incident). Put the identifier in `material_number`,
  not `name`. If the source's name field is identifier-only and no
  descriptive name is recoverable from the source, flag it to the user
  rather than importing bare identifiers as names.
- Prices (`price`, `after_hours_price`, `unit_cost`) in **dollars**
  (`15.50`) — divide by 100 if the source has cents.

**EQUIPMENT** (`equipment.csv` / `equipment-non-importable.csv`)
- Required: `equipment type`.
- Headers (exact order): `equipment type, name, manufacturer, model
  number, serial number, install date, placement, status, manufacturer
  warranty end, notes, customer number, location number, customer name,
  customer email, customer phone, street address, unit, city, state, zip,
  country, property type, job location`

**MEMBERS** (`members.csv` / `members-non-importable.csv`)
- Required: `contact name`.
- Headers (exact order): `contact name, phone number, email, service
  address, membership plan, number of systems, start date, is auto
  renewal?, next auto renewal, end date, last service date, next outreach
  date, notes, country, status, notes.1`

**⚠️ Re-running the cleaning script after some entities are already
uploaded silently wipes their post-upload triage.** If a single script
(or shared function) rebuilds *all* `cleaned-data/<entity>.csv` files
from `raw/` in one pass, re-running it to pick up a fix for one entity
(e.g. a corrected Estimates re-scrape) **also regenerates every other
entity's `cleaned-data/<entity>.csv` and `<entity>-non-importable.csv`
from scratch** — silently discarding any rows you'd already moved to
`-non-importable.csv` after a real Lighthouse upload (per the
"Triaging failures" process in Phase 3 below). Confirmed in
practice: re-running cleaning to fix Estimates reset `jobs.csv` and
`invoices.csv` back to their pre-upload row counts, silently undoing the
post-upload failure triage for two already-completed entities. **After
any re-run of the cleaning step, re-check whether any entity's
`cleaned-data/` files need their post-upload triage redone** — keep the
downloaded Lighthouse error-report CSVs around (per the
`~/Downloads/failures-<timestamp>/` convention) specifically so this is
quick to redo, not just for the initial triage.

### Final reporting for the cleaning phase

Once cleaning completes, produce a summary table with, per file: file
name, clean row count, non-importable row count, column count. Plus:
count of merged duplicate contacts, count of junk phones dropped, count of
property-management groups safely left unmerged, and a brief log of
judgment calls made or fields that couldn't be mapped.

### Known FSM data quirks catalog

A running list of confirmed per-FSM data quirks — dirty patterns that
looked like they might need a special fix, what turned out to be true,
and what fix (if any) was actually correct. This is the reference the
judgment-call gate above tells you to consult whenever you spot obviously
dirty data in any entity: multi-day/multi-week job spans, suspiciously
repeated identical dates/times across many job/estimate/invoice records,
or anything else that doesn't cleanly fit the documented cleaning rules.

**How to use this catalog:**
1. **Detect** — quantify the pattern in the actual data (row/gap counts,
   a couple of concrete examples), don't just eyeball it.
2. **Consult** — check the table below for an entry matching either this
   exact FSM, or a *different* FSM with a similar-looking symptom.
3. **Explain and confirm — always, even for a quirk already confirmed on
   this exact FSM before.** "Known" doesn't mean "apply without asking";
   it means you already have the explanation and fix ready to present.
   Tell the user what you found, cite the catalog entry (or the absence
   of one), and offer the fix — get explicit confirmation before applying
   it, per the judgment-call gate above.
   - If the symptom matches a *different* FSM's entry, say so explicitly
     and don't assume the same root cause applies — verify the offered
     fix against *this* FSM's actual raw data before applying it, not by
     blindly porting the other FSM's fix. (The HouseCall Pro → Jobber
     case below is the cautionary example: the symptom looked identical,
     but the root cause and correct fix were different.)
   - If nothing in the catalog matches, this is a **novel quirk** — you
     **MUST** flag it to the user with your suggested fix option(s) and
     ask how they'd like to proceed. Do not silently apply a default for
     an undocumented pattern.
4. **Extend** — once resolved, add a new row (or update an existing one)
   below with what was actually learned, including the FSM, the symptom,
   the root cause, the fix, and whether it needs standing confirmation
   each time (it always does, per step 3) or was a one-off.

| FSM | Symptom | Root cause | Fix | Notes |
|---|---|---|---|---|
| HouseCall Pro | Job `start`/`end` differ by >~24h | Genuine multi-day visit — the source's own end date is reliable here | `job_start_date` = end minus 1 hour (`build_job_start_end_multiday_variant`) | Confirmed correct for HCP specifically (Apex Residential migration). **Offer, don't auto-apply** — see the JOBS schema note above. |
| Jobber | Job `start`/`end` differ, sometimes by years | Two unrelated things masquerading as one symptom: (a) `endAt` on recurring/membership jobs can carry a far-future sentinel value unrelated to any real visit; (b) even short, real-looking gaps are usually just "closed a few days after it was scheduled," not a real multi-day span | Use the raw scraper's own explicit `job_start_date`+`start_time` fields directly (`build_job_start_end`'s default path) — don't derive from `end` at all except when `start` is genuinely absent | The HouseCall Pro end-derived fix was tried here first and found to corrupt ~2,228/2,237 (99.6%) of ONE_OFF jobs — see the superseded-finding writeup in the JOBS schema section above. This is the cautionary example for step 3 above: identical-looking symptom, different FSM, wrong fix. |
| Jobber | Membership `end_date`/`next_auto_renewal` land on suspicious round-number spans (365, 731, 1827, 2191, 3653 days) whenever `is_auto_renewal` is true | Same root cause as the Jobber jobs entry above — both fields are derived from the source job's `endAt`, which carries the same sentinel-value bug | Blank `end date`/`next auto renewal` outright when `is auto renewal?` is true, rather than passing the sentinel through | See the MEMBERS-adjacent note under the JOBS schema section. Same underlying `endAt` quirk, different entity — a reminder to check every date field derived from a Jobber `endAt` value, not just Jobs. |

This table starts thin — add to it every time a migration on a new FSM
(or a new quirk on an already-listed FSM) gets resolved. The value of
this catalog compounds the more FSMs get covered: a future migration on
an FSM never seen before is exactly when "does this symptom match
anything we've already figured out" is most useful to check first,
rather than re-deriving root-cause analysis (like the Jobber date
investigation above) from scratch.

## Phase 3 — Upload (the Lighthouse FSM Data Transformer wizard)

Pushes a customer's cleaned CSV data — **any entity produced by the
scrape+clean pipeline: contacts, job history, invoices, estimates,
pricebook materials/services, memberships/members, equipment, etc.** —
into Podium through Lighthouse's **FSM Data Transformer** wizard, then
triages any import failures into reconcilable-retry vs.
genuinely-non-importable buckets. The wizard mechanics, error-triage
workflow, and file conventions below are the **same regardless of which
entity you're uploading** — only the field-mapping specifics differ per
entity (documented as they're discovered; Job History is the
most-thoroughly-documented example so far, but treat its quirks as
illustrative of the pattern, not as the only entity this applies to).
This phase is the entry point for a **standalone re-upload/retry
request** too — it doesn't require having just run Phase 1/2 yourself, as
long as `cleaned-data/` already has upload-ready CSVs. Driven entirely
through `mcp__claude-in-chrome__*` browser automation — there is no API.

Load the core Chrome tools before starting if not already loaded:

```
ToolSearch("select:mcp__claude-in-chrome__tabs_context_mcp,mcp__claude-in-chrome__navigate,mcp__claude-in-chrome__computer,mcp__claude-in-chrome__read_page,mcp__claude-in-chrome__find,mcp__claude-in-chrome__file_upload,mcp__claude-in-chrome__tabs_create_mcp")
```

### Prerequisites

- The user (or you) must be on the correct customer's Lighthouse location
  page (`https://lighthouse.podium.com/locations/<org-uuid>/<location-id>`),
  **"Data Migration" tab**. The URL is customer-specific — ask the user for
  it if you don't have it (`?tab=data-migration`).
- You need a local **working directory** for this customer with a
  `cleaned-data/` folder of upload-ready CSVs — normally produced by
  Phase 1 (scrape) and Phase 2 (clean) above, but a standalone re-upload
  request works just as well if the user hands you already-cleaned CSVs
  directly. See "Folder conventions" near the end of this file for the
  expected layout.

### Prerequisite: get Business Units, Job Types, and Technicians into Podium before mapping

**⚠️ This is a hard ordering requirement, not a best practice — adding
users/technicians NEEDS to happen before Job History is uploaded, every
time, with no exceptions.** Do this before running Job History (or
Invoices/Estimates) through the wizard — check it every time, not just when
something looks off. This is also the "Users/Technicians" entity from the
skill-wide completeness principle at the top of this file: the source
FSM's staff roster is a real migration deliverable, not just a mapping
unlock — every active technician in the roster should end up as a Podium
user designated as a Technician (see the "Podium side — creating the
users + designating technicians" steps below), and that has to be done
before Job History runs, because there's no batch way to attach
technicians to jobs after they're already imported. The
Technician Mapping and Job Type Mapping sub-steps (see "Known
entity-specific quirks" below) match against whatever business units, job
types, and technicians already exist in the customer's live Podium
account. If the Lighthouse checklist's **"Business Unit / Job Type /
Technician Setup"** row is `NOT STARTED`, that account usually has close
to nothing configured — a handful of `NOT STARTED`-implied defaults but no
real taxonomy — so the AI mapping step will come back **~0% / "no match"
on nearly every row**, and every job will import with no job type and no
technician. That's not a data-quality problem to route around; it means
the setup step hasn't happened yet, and it's usually worth doing before
the main upload rather than after.

**How to check and fix it, using the live product account (same Mock flow
as "Investigating directly in the customer's Podium account" below):**

1. From the Lighthouse location page, hamburger menu (☰) → **Open
   Organization in Admin** → **Mock** (not Support Mock) → this opens
   `app.podium.com` logged into the customer's real account.
2. **Business Units & Job Types** — Settings → FSM Configurations →
   Operations → Business Units & Job Types.
   - A **Business Unit** is just a name plus a Trade (HVAC / Plumbing /
     Electrical / General) and a Division (Service / Install /
     Maintenance / Sales) — a 2-axis picker, not free text. Derive the
     actual set of units from the source data's own structure (e.g.
     ServiceTitan's own `Business Unit` column, cross-referenced against
     each job type's real trade) rather than inventing a taxonomy from
     scratch — but **propose the structure to the user and get
     confirmation before creating anything**, per the skill-wide
     judgment-call rule: this shapes how the customer's team sees their
     jobs categorized going forward, not just an import mapping detail.
   - Each **Job Type** needs a Name (make it byte-identical to the
     source's distinct job-type values so the mapping step's exact-match
     logic actually fires), a Business Unit, and a required **Duration
     (minutes)** field the source data has no reliable signal for —
     don't invent a per-type duration from noisy elapsed-time data;
     confirm a flat default (60 min worked fine) with the user first.
   - **For more than a handful of job types, the UI is too slow to use
     one row at a time.** A fast, verified-safe path: create *one* job
     type by hand while a `fetch`-intercepting script
     (`javascript_tool`) is installed on the page, read the captured
     GraphQL mutation (`Hvac_CreateJobType` against the app's own
     `magic.podium.com/graphql`, called with the page's own live
     `Authorization` header), then replay that same mutation directly
     from the browser console in a loop for the rest of the list. This
     created 129 job types across 8 business units in under a minute
     with zero failures in practice — far faster than clicking through
     the modal 129 times. The `assignEmployeeJobTypes` mutation
     (captured the same way from one manual technician job-type save)
     works the same way for bulk-assigning technicians to job types in
     one call per technician instead of one click per checkbox.
3. **Technicians** — Settings → FSM Configurations → Operations →
   Technicians. **Check Podium's existing Users first**
   (Settings → Users → All Users) — the people are very often already
   Podium users (they just haven't been designated as technicians yet),
   so this is usually "add existing user as technician," not "invite a
   new user." Only send an invitation email for someone who's genuinely
   not already a user, and confirm with the person asking before sending
   any invite.
   - **Cross-reference the source FSM's own *current* technician/employee
     roster** (e.g. ServiceTitan's own Settings → People → Technicians,
     filtered to Active) **against the job history's technician column
     before deciding who to add.** Job history commonly spans years or
     decades and carries dozens of former employees' names that will
     never match a live Podium user and shouldn't be created — in one
     migration, 91 distinct technician names appeared in the job history
     but only 3 were still active per the source system's own technician
     list; the other 88 were correctly left unmapped.
     - **⚠️ Verify you're signed into the correct customer's account
       before reading anything from the live source FSM (technician
       rosters, employee emails, current job types, etc.) — this browser
       is commonly signed into several different accounts on the same
       source system at once** (e.g. multiple ServiceTitan tenants), and
       nothing forces the tab you're looking at to be the customer you're
       currently migrating. Confirm the account/company name shown in the
       source system's own UI (header, org switcher, settings page)
       matches the customer before treating anything you read there as
       real. **One practical cross-check once you're looking at people/
       employee records: does each person's email address plausibly
       belong to this business** — matching the customer's own name or
       domain — rather than looking like it belongs to a different
       company entirely. A roster full of emails that don't relate to the
       customer at all is a sign you're in the wrong account, not a sign
       the data is just messy. This is the same class of mistake as the
       "Mock sessions drift to other customers" issue documented below
       for the Podium side — it applies symmetrically to the source-FSM
       side, and is worth checking every time, not just once per session.
     - **HouseCall Pro's current roster** is at **Settings → Team &
       Permissions → Team** (the "Employees" list). Each row shows a
       Role (Admin / Field Tech / Office Staff). **Click a person's name**
       to open their detail page; **Personal details** shows their email
       and mobile phone (`get_page_text` on
       `/app/settings/employees/pro_<id>/personal_details` reads these
       without a screenshot). Add as Podium technicians the people whose
       HCP role is **Field Tech**, plus any **Admin** who actually appears
       in the scraped `Jobs`/`Estimate Appointments` `technician` column
       with real volume (working owner / lead tech). Skip Office Staff,
       skip the CSR/dispatch Admin who only shows up authoring job notes,
       and skip every job-history name **not** on this current roster
       (confirmed on Today Air: 12 distinct names in job history, only 7
       on HCP's live 10-person roster — the other 5 were former employees
       and were correctly not created).
   - **Podium side — creating the users + designating technicians:**
     1. **Settings → Users → "Invite users"** opens a multi-row form
        (Email / First name / Last name / **Role** dropdown, with an
        "Invite another" button to stack rows). Set **Role = "Technician"**
        on every row and click **"Create & invite"** — this creates the
        user account *and* emails them an invite in one step (confirm with
        the user before sending, per the note above; Today Air's user
        explicitly authorized it). Verify in **admin.podium.com → org →
        Users tab → "Technician" filter** that every account was created.
     2. **Settings → FSM Configurations → Operations → Technicians →
        "+ Technician"** — the dropdown lists every Podium *user* (the
        Technician *role* from step 1 does NOT auto-populate this list;
        it's a separate designation). Type the name in the dropdown's own
        "Search users" box (not the page's outer Search), then click the
        filtered result. A "Technician added" toast fires.
     3. **⚠️ This list does not refresh live — and a hash-nav reload is
        not enough.** After adding people it keeps showing "No
        technicians assigned yet" / a stale subset even after
        re-navigating the `#/…` URL; the adds only became visible after a
        **full document reload in a freshly-Mocked tab**. On Today Air,
        two names (Kainon Schill, Kyle Brown) appeared "missing" through
        ~4 hash-nav reloads and looked like failed writes — they had
        actually persisted all along and showed up once a brand-new Mock
        tab loaded the page from scratch. So: don't trust the count in a
        long-lived Mock tab; verify in a fresh Mock, or via
        **admin.podium.com → org → Users → "Technician" filter** (which
        shows the user accounts) plus one fresh Operations → Technicians
        load for the designation. Don't re-add on apparent failure until
        you've checked a fresh session.
     4. **⚠️ Mock sessions drift to other customers.** The mocked
        `app.podium.com` session token expires after a few minutes and the
        next navigation silently lands you in a *different* customer's
        account (seen repeatedly on Today Air: "Mocked in as [someone
        else]", a different `locationUid`, another org's home screen —
        J & J Air and Warner Super Service both came up mid-task).
        **Before any write in a mocked tab, confirm the top-left account
        name and the yellow "Mocked in as …" banner match the target
        customer.** If it drifted, close the tab and re-Mock fresh from
        admin.podium.com → org → **Mock**. Combined with the no-live-
        refresh issue above, the safe rhythm is: re-Mock fresh → make a
        few edits fast → close the tab → re-Mock fresh to verify.
   - **Assign each technician's job types based on what they've actually
     worked in the source history**, not a blanket "every tech does
     everything" — derivable by cross-referencing the technician column
     against job type/job id in the raw scrape. Confirm the granularity
     with the user first (e.g. every job type they've ever touched, vs.
     only ones with some minimum job count) per the judgment-call rule —
     this is a real judgment call, not a mechanical step.
4. **Back in the wizard**, on the Technician Mapping / Job Type Mapping
   sub-steps, click **Refresh Technicians** / **Refresh Job Types**. These
   AI suggestions are computed once when the sub-step first loads and do
   **not** auto-update when you fix the underlying Podium data in another
   tab — you have to explicitly refresh, and the refreshed match list can
   be virtualized/incomplete in the rendered DOM even after a real
   refresh succeeded, so verify via the endpoint response (or a solo-row
   spot-check) rather than trusting what's visibly rendered alone if the
   list is long.

### Supported entities & upload order

The standard scrape+clean pipeline (see "Folder conventions" near the end
of this file) produces one `cleaned-data/<entity>.csv` per entity. Each
maps to a specific checkbox label in the wizard's **Target Tables**
multi-select — the label doesn't always match the filename exactly:

| `cleaned-data/` file                              | Target Tables label                  |
|---------------------------------------------------|---------------------------------------|
| `customers.csv`                                   | Contacts                              |
| `jobs.csv`                                         | Job History                           |
| `invoices.csv`                                     | Invoices                              |
| `estimates.csv`                                    | Estimates                             |
| `pricebook-materials.csv`                          | Pricebooks (materials sub-type)       |
| `pricebook-services.csv`                           | Pricebooks (services sub-type)        |
| `members.csv`                                      | Memberships / Members                 |
| `equipment.csv`                                    | Equipment                             |

**Membership Plans and Estimate Templates have no Target Tables entry at
all** — they're not part of the CSV pipeline. Both checklist rows route
through Lighthouse's **"Set Up ___ with Operator"** flow instead (see the
"Membership Plan Mapping" quirk note above for the full mechanics) — per
the completeness principle at the top of this file, treat them as a
standing, required step for every migration (not something to leave
`NOT STARTED` just because it isn't a CSV upload), not something
`cleaned-data/` ever produces a file for.

`equipment.csv` is commonly **skipped entirely** by the cleaning step if
the source system has no real structured equipment data (e.g. Jobber only
has placeholder custom-field text) — check `cleaned-data/_audit.json` or ask
the user before assuming it should exist.

**Upload order matters** — later entities reference earlier ones, so
uploading out of order produces avoidable "not found"/"could not be
matched" failures:
0. **Users/Technicians (with Business Units and Job Types) NEEDS to happen
   before Job History** — this isn't a CSV-wizard step, it's the Mock-based
   setup in "Prerequisite: get Business Units, Job Types, and Technicians
   into Podium before mapping" above. Do it first, every time — Job History
   imported before the roster exists comes in with no technician assigned
   and there's no batch way to fix that up afterward.
1. **Contacts** (customers) first, and let it finish.
2. **Job History** next (jobs reference their customer's Contact — see
   the "reconcilable isn't the same as will succeed" lesson below).
3. **Invoices** and **Estimates** last (these commonly reference both the
   customer *and* the job — in bulk-upload mode they get explicitly
   linked to jobs via `job_id`, see "Bulk mode" below).
4. Pricebook (materials/services), Memberships, etc. are generally
   independent of the above and can go in any order — no dependency
   issues observed for those (steady 100%-success runs in practice).
   **Equipment is the exception: the wizard hard-requires a Contacts
   sheet in the same upload** (uploading `equipment.csv` alone on Step 1
   errors with "Equipment import requires a contacts sheet in the same
   upload. Add a contacts sheet to the file and upload again.") — always
   upload `equipment.csv` bundled together with `customers.csv` in one
   multi-file CSV upload (Target Tables: Equipment + Contacts), even if
   Contacts already completed its own standalone run earlier. This
   triggers bulk mode's Cross-Sheet Key Links screen (see below) —
   Remove All the AI-proposed links (they tend to be spurious,
   e.g. `unit↔unit`, `contact_notes↔notes`) and manually add
   `customers.email → equipment.customer_email` as the real join key.
   **If Transform then fails with "Equipment sheet without contacts
   sheet"** even though both sheets were uploaded together (seen when
   the `customers` sheet mapping showed a `SAVED` badge, reusing a
   mapping cached from an earlier session) — click **Start Over** to
   fully wipe the session and redo Upload → Mapping → Cross-Sheet Key
   Links → Preview → Transform from scratch with both files. That
   resolved it cleanly on the first retry (28/28 equipment rows
   imported). Also, Equipment's Review step header stats can show
   `Completeness 0%` / a nonzero "Rows Needing Review" count even when
   every row scores green and `Errors only`/`Warnings only` both read
   0 — a cosmetic stat quirk, not a real blocker; trust the per-row
   scores and error/warning tab counts instead.
   **Pricebook is the opposite case from Equipment: never bundle
   `pricebook-services.csv` and `pricebook-materials.csv` into the same
   upload, even though both map to the same single Target Tables checkbox
   ("Pricebooks") and it's tempting to treat them like one multi-file bulk
   upload.** Podium classifies an entire uploaded *sheet* as `SERVICES` or
   `MATERIALS` as a whole, from that sheet's first-row column headers (the
   Mapping step says so explicitly: "Pricebook worksheets are classified
   as Services or Materials from the first-row column headers... Each
   sheet maps to one Tempest import type") — there is no per-row/per-item
   classification. Uploading both files together in one `file_upload` call
   also spuriously triggers the multi-file "Cross-Sheet Key Links" screen
   (see "Bulk mode" below) with nonsense proposed joins between the two
   unrelated sheets (e.g. `category↔category`, `price↔price` across
   services and materials) even though only one Target Table is checked —
   this isn't limited to genuinely multi-entity Target Table selections.
   Podium's own native product import (Settings → Pricebook → "..." →
   Import CSV) independently confirms the same one-type-per-file model via
   its own "Select Import Type" modal, which forces a binary
   Materials-or-Services choice per import. **The correct approach: run
   the FSM Data Transformer wizard twice for pricebook, once per file** —
   Upload → Mapping → Preview → Transform → Review with only
   `pricebook-services.csv` (classifies as SERVICES), **Start Over**, then
   repeat the same five steps with only `pricebook-materials.csv`
   (classifies as MATERIALS). Never combine them into one merged CSV
   either — that just relocates the same bug, since the wizard still
   classifies the whole merged sheet as one type from its header
   signature, silently mistyping every row of the other type.

If working through a **full multi-entity migration** rather than a single
targeted re-upload, do the whole sequence — contacts through
invoices/estimates through everything else — before considering a
rescrape (see "The rescrape decision" below).

### Pre-flight: what a "full migration" always skips

Before touching any row's Actions menu, read the checklist's **Last ETL
Status** column for every entity (screenshot or `get_page_text` the whole
table first — don't assume state, verify it):

- **Skip any row already `REVIEWED` or `N/A`.** These are finalized —
  `REVIEWED` means the data was confirmed correct with the customer
  ("Data Reviewed with Customer"), `N/A` means someone deliberately
  decided that entity doesn't apply to this customer ("Mark N/A"). Do not
  click Transform & Upload, do not Start Over, do not re-touch these rows
  at all. Re-running a transform on a reviewed/N/A row risks duplicating
  data the customer already signed off on or silently overturning a
  deliberate N/A call that isn't yours to reverse.
- **Skip `Attachments` unconditionally**, regardless of its status. It's
  not part of the standard scrape+clean pipeline this skill covers (no
  `cleaned-data/attachments.csv` is produced) and this shop's standing
  process is to leave attachments out of migrations entirely (consistent
  with rescrapes also being run "without attachments" — see "The rescrape
  decision" below).
- A "full migration, excluding reviewed/N/A and Attachments" therefore
  means: every remaining entity row (`NOT STARTED` / `FAILED` /
  `COMPLETED W/ERR`, or `COMPLETED` if re-running is intentional) that
  isn't `REVIEWED`, isn't `N/A`, and isn't Attachments. If a row's status
  is ambiguous from the checklist alone, check its **History** tab or ask
  the user rather than guessing whether it's safe to touch.

### Page anatomy: the checklist

The Data Migration tab shows a **Checklist** (toggle vs. **History**),
grouped into phases (e.g. "Phase 1 — Foundation", "Phase 2 — Core
Reference Data", "Phase 3 — Everything Else"). Each row is one entity
(Contacts, Job History, Pricebook — Materials/Services, Members, Estimates,
Invoices, Technicians, Call/Job Notes, Attachments, Tags/Customer Notes,
Membership Plans, Seasonal Scheduling, Automations, ...) with columns:
Last ETL Status (`NOT STARTED` / `COMPLETED` / `COMPLETED W/ERR` / `FAILED`
/ `N/A` / `REVIEWED`), Last Date, Last Results (`N success · M failed`,
clickable), In Product (row count), and an **Actions** dropdown with:
**Transform & Upload**, **Upload with Operator**, **Set Up Job History /
Recover with Operator** (entity-specific), **Data Reviewed with Customer**,
**Mark N/A**.

A **remediation banner** above the checklist (e.g. "Job import needs
remediation — 1552 ROWS (100%) MISSING_CONTACT_REF — verify the contacts
import completed before jobs, then re-run the job import...") tracks
cross-entity blockers. Its row count shrinks as you fix the underlying
issue (e.g. 1552 → 272 → 16 as Contacts got repaired) — treat it as a
live progress indicator while iterating, not a one-time read.

**⚠️ Confirmed with the user: this banner is often wrong — don't trust
its number over what you directly observe from an actual upload's Review/
Import-progress results.** Seen in practice: a Job History upload that
directly resulted in 2,343 imported / 184 failed (92.7% success, out of
2,527) was immediately followed by the banner jumping from "14 ROWS
(100%)" to **"362 ROWS (98%) MISSING_CONTACT_REF"** — a number with no
apparent relationship to the upload that had just completed. It likely
aggregates stale state across multiple upload attempts (including old
sessions) rather than reflecting current reality. Use the per-upload
Review screen's actual counts (and the downloaded error report) as the
source of truth for what did and didn't import; treat the banner as a
rough "something might still need attention" nudge, not a number to
report, react to precisely, or reconcile against your own row counts.

### The FSM Data Transformer wizard

Click a row's **Actions → Transform & Upload** to enter the wizard. It has
5 steps: **Upload → Mapping → Preview → Transform → Review**.

**⚠️ Resuming vs. fresh session:** if that entity has an unfinished or
previously-failed transform, clicking Transform & Upload **resumes that
saved session** (can jump straight to step 5/Review with old data still
loaded) instead of starting fresh at Upload. To start clean, click
**"Start Over"** (top right) first — confirm the "Start over?" modal. Only
skip Start Over if you deliberately want to pick up/retry that exact same
batch.

#### Step 1 — Upload

Fields: Customer Name (pre-filled, read-only in practice), **Source FSM
System**, **Target Tables**, **Upload format** (Excel workbook / JSONL
files / CSV files toggle), then a file drop zone matching that format.

- **Source FSM System is a native `<select>`.** Its options render in an
  OS-level popup that **screenshots can't see and clicking an option `ref`
  does not reliably select** (browser_automation clicks land but the value
  doesn't stick). Instead: click the select to focus it, then press the
  first letter of the desired option as a `key` action (browser typeahead)
  — e.g. `key: "o"` selects **"Other"**. Screenshot afterward to confirm
  the value actually changed. For data sourced from **Jobber**, there is
  no "Jobber" option in the list (Housecall Pro, FieldEdge, Service
  Fusion, Profit Rhino, Payzerware, QuickBooks, ServiceTitan, Other) — use
  **"Other"**.
- **Target Tables is a custom multi-select** (search box + checkboxes:
  Memberships, Pricebooks, Job History, Contacts, Invoices, Estimates,
  Equipment, ...) — plain clicks work normally here. Pick the single
  entity matching the file you're uploading (e.g. "Job History" for a
  jobs CSV — there's no literal "Jobs" option).
  - **Bulk mode**: selecting *multiple* Target Tables at once (e.g. Job
    History + Invoices + Estimates in one pass) surfaces a **"Cross-Sheet
    Key Links"** screen as the first part of Step 2/Mapping, before the
    per-sheet field-mapping tables. It auto-proposes ~15-20 links between
    every pair of sheets that share a column name, each with an AI
    confidence % and "N% of sample rows match." **Verified in practice:
    most of these are spurious** — e.g. `invoices.total_cents ↔
    estimates.total_cents`, `jobs.status ↔ invoices.status`,
    `*.notes ↔ *.notes`, `*.line_items_json ↔ *.line_items_json` are
    independent fields on unrelated entities that only coincidentally
    share a column name; confirming them wrongly is a very available
    trap here, so don't accept them on confidence-% alone. **This shop's
    standing rule for this screen: click "Remove All" first, then
    manually add exactly two links via the "Add a key link manually"
    tool at the bottom — `estimates.job_id → jobs.job_id` and
    `invoices.job_id → jobs.job_id`** (both are real foreign keys; the
    phone/email cross-sheet pairs the AI also proposes are not part of
    this rule, even though they look like plausible identity bridges —
    don't add them unless told otherwise). The manual-add tool's four
    dropdowns (`Sheet`/`Column`/`Sheet`/`Column`) are native `<select>`s
    — use the same click-then-`key`-typeahead technique as Source FSM
    System above, not plain clicks. "Proceed to Mapping" stays disabled
    until every proposed link is either confirmed or removed, so
    "Remove All" is the fast path to a clean slate before adding the two
    manual links.
- **Upload format**: match your file — CSV files for `.csv`, drag/drop or
  use `file_upload` on the file-input `ref` (found via `find`, query like
  "CSV Files file input drop zone"). **Do not click the drop zone
  directly** — that opens a native file picker `computer` can't see; go
  straight to `file_upload` with the input's `ref`.
  - **For bulk mode, pass all the CSVs in one `file_upload` call** —
    e.g. `paths: [".../jobs.csv", ".../invoices.csv", ".../estimates.csv"]`
    against the same CSV-files input `ref`, matching however many Target
    Tables you checked. The "Parsed sheets" panel lists all of them with
    their own row/col counts and an auto-detect entity-type dropdown
    each — sanity-check the counts against your `cleaned-data/` files
    before clicking Upload & Analyze, same as single-file mode.
    (`file_upload`'s combined-size cap is 10MB across all files in the
    call — fine for typical entity CSVs, but watch it on a very large
    invoices/jobs file.)
  - **⚠️ A CSV too big to upload doesn't need to be split just to get it
    into the wizard — gzip it.** The CSV drop zone's own label reads
    "Drag and drop .csv, .csv.gz, or .zip files here" and its
    `input[type=file]` carries `accept=".csv,.gz,.zip"`, so **`.csv.gz`
    is a first-class input** — the wizard decompresses it server-side and
    the "Parsed sheets" panel reports the full uncompressed row count as
    if you'd uploaded the plain CSV. This clears two separate ceilings at
    once: `file_upload`'s 10MB-per-call cap, and the wizard's own stated
    50MB limit. Confirmed on a real 76,523-row ServiceTitan invoices file:
    **52MB raw → 7.7MB with `gzip -9`** (line-item JSON compresses
    roughly 7:1). One command: `gzip -9 -c cleaned-data/invoices.csv >
    cleaned-data/invoices.csv.gz`. Verify the round-trip before uploading
    (read the `.gz` back with `gzip.open` and count rows) so a truncated
    write can't silently cost you rows, then confirm the wizard's parsed
    row count matches your local count.
  - **⚠️ Gzip only fixes the upload step — it does NOT fix a separate,
    row-count-driven stall in the actual "Upload to FSM" import step for
    a very large entity.** Confirmed the hard way on that same
    76,523-row invoices file: gzip got it through Upload → Mapping →
    Preview → Transform → Review fine as one file, but clicking **Upload
    to FSM** on the full 76,523-row sheet stalled indefinitely at ~14%
    (checkpoint frozen for 2+ hours, confirmed via the backend
    `/api/data-transformer/import-status/<jobUid>` API, not just the UI
    spinner — see "Diagnosing a stalled/frozen import" below) and never
    recovered. **The fix that actually worked: split the CSV into
    ~10–20k-row CSV parts (plain, not gzipped — they're small enough
    already) and run the wizard once per part, sequentially** (Start
    Over → fresh Upload → same Target Tables/mapping each time — the
    mapping step re-confirms itself instantly since column names don't
    change between parts). This is safe and idempotent: Podium dedupes
    Invoices by `external_id`, so if an earlier abandoned/stalled attempt
    partially processed some of those same rows, re-uploading them again
    in a part is a no-op, not a duplicate. A Python split that keeps the
    header on every part and stays under ~9.5MB per part (well under both
    ceilings) is enough:
    ```python
    import csv
    TARGET_BYTES = 9_500_000
    with open('cleaned-data/invoices.csv', newline='', encoding='utf-8') as f:
        reader = csv.reader(f); header = next(reader)
        part_idx, rows, size = 1, [], len(','.join(header).encode())+2
        def flush(rows, idx):
            with open(f'cleaned-data/invoices-parts/invoices_part{idx:02d}.csv','w',newline='',encoding='utf-8') as out:
                w = csv.writer(out); w.writerow(header); w.writerows(rows)
        for row in reader:
            line_bytes = len(','.join(row).encode())+2
            if size + line_bytes > TARGET_BYTES and rows:
                flush(rows, part_idx); part_idx += 1; rows = []; size = 0
            rows.append(row); size += line_bytes
        if rows: flush(rows, part_idx)
    ```
    Verify the split's row total matches the original file's before
    uploading anything (`sum(len(part) for part in parts) ==
    len(original)`).

  #### Diagnosing a stalled/frozen import
  **The in-wizard progress bar and the checklist's "IMPORTING" badge are
  not reliable signals of whether an import has actually stalled** — read
  the backend checkpoint directly instead of guessing from the UI. Every
  active or completed import job has a status endpoint at
  `/api/data-transformer/import-status/<jobUid>` (grab the `jobUid` from
  a `read_network_requests` call filtered on `import-status` right after
  clicking Upload to FSM). Its JSON includes a `checkpoint` object
  (`succeeded`, `failed`, `completedChunks`, `totalRows`) that updates in
  real time while genuinely processing. **Poll it directly via
  `fetch(url, {credentials:'include'})` in `javascript_tool` — don't rely
  on reloading the wizard page**, which can itself return a stale,
  frozen snapshot even when the backend is fine (confirmed: the wizard's
  own Review-step "Import progress" line showed the identical stale
  count across multiple page reloads while the direct API call showed
  real, moving numbers).
  - **A genuine stall looks like an unchanging `checkpoint` across
    several polls spaced 30–60s apart** (not just a slow chunk — this
    migration's imports naturally decelerate as they approach 100%, so
    don't call it stalled until the count is flat for several minutes).
    There is no error, no `pathologies` entry, nothing — it just stops
    advancing. Confirmed twice on unrelated sessions in one migration, so
    this is a real, recurring platform behavior, not a one-off fluke.
  - **The fix, confirmed to work both times: abandon the stalled session
    (Start Over — this only wipes client-side wizard state, it does not,
    and cannot, cancel the stuck backend job; there is no cancel button
    anywhere in the UI) and re-upload the same file (or the same file
    split into smaller parts if the whole-file upload is what stalled) in
    a brand-new session.** This is safe specifically because the target
    entity's import is idempotent on its own identifier
    (`external_id` for Invoices/Estimates) — a row that the stalled job
    already silently created lands as a harmless "already exists"-style
    no-op on the fresh attempt, not a duplicate. Don't try to salvage or
    resume the stalled job; there's no UI or documented API to do so, and
    waiting it out has taken 2–3+ hours with zero recovery in every case
    observed so far.
  - **⚠️ After clicking "Upload to FSM," verify the job actually started
    before walking away** — confirmed once that the click can silently
    fail to register (the Review step reverts to showing the un-uploaded
    "Approve Sheet"/"Upload to FSM" buttons instead of "Approved — click
    to undo" / "Uploading…", with no error), leaving nothing running at
    all while you wait on a job UID that returns an empty
    `{"importStatus":null,"importJobs":[]}` forever. After clicking
    Approve Sheet then Upload to FSM, re-check the button text/aria state
    and poll the import-status endpoint once immediately — confirm
    `status` reads `"pending"` or `"importing"` (not an empty
    `importJobs` array) before considering the upload actually launched.

  #### Failure-reason taxonomy for a "job not found" batch (beyond the
  reconcilable-vs-source-gap check already documented above)
  When cross-referencing a batch of `"No customer_uid provided and job
  not found for job_id 'X'"` failures against `jobs.csv` ∪
  `jobs-non-importable.csv`, a job_id can land in one of **three**
  buckets, not two — don't assume "not in jobs.csv" always means
  "already in jobs-non-importable.csv":
  1. **In `jobs.csv`** — genuinely retriable (the job import just hasn't
     landed yet relative to this entity's upload ordering).
  2. **In `jobs-non-importable.csv`** — a known, already-explained
     exclusion. No new information, no action.
  3. **In neither file** — the job_id was never captured by the Job
     History scrape at all. Confirmed on a real migration: 8,177 Invoice
     rows referenced job_ids in a completely different numeric range
     (7-digit, ~4,000,000+) than the rest of the dataset (6-digit,
     ~900,000s), all absent from both files — a strong signal of a real
     **scraper coverage gap** (a distinct business unit, job-type filter,
     or pagination boundary the Job History exporter never reached), not
     a normal exclusion. **This is a finding to flag to the user, not
     something to silently lump in with case 2** — per the "rescrape is a
     last resort" rule, don't act on it (don't rescrape) mid-entity, but
     do call it out distinctly in the final report so the user can decide
     whether it's worth a targeted rescrape once the full audit is done.

  #### When a validation failure is reproducible, not transient
  Not every non-"job not found" failure is a data problem worth chasing
  in the CSV. Two confirmed patterns from one migration's Invoices
  entity, both worth checking for on any large batch:
  - **A batch of failures with a raw stack-trace-shaped message** (e.g.
    `%Finch.TransportError{reason: :closed, source: ...}`) **is a
    transient backend connection error, not a data problem** — worth one
    retry via the session's own "Retry Upload to FSM" before concluding
    anything about the rows.
  - **But don't assume every odd message is transient — verify by
    retrying once and comparing failure counts/row numbers before and
    after.** Confirmed on the same entity: 96 rows failing with
    `"subtotal_cents is required and must be a valid amount"` retried to
    the **exact same 96 row numbers, byte-for-byte**, despite
    `subtotal_cents` being present, numeric, and matching its line-items
    JSON sum on every one of those rows (checked line-item quantity
    types, cross-part duplicate external_ids, and raw CSV bytes — all
    clean). An unchanged retry result across the identical rows is the
    tell that this is a genuine backend defect on Podium's side, not a
    CSV issue — stop investigating the data and flag it as a
    support-ticket item with the specific external_ids/row numbers
    instead of guessing further.
  - **A single genuinely invalid value is still possible and worth a
    quick real check before assuming it's the same backend bug** — e.g. a
    lone `"tax_amount_cents is not a valid cents amount: -48900"` traced
    back to one row where `subtotal_cents=48900`,
    `tax_amount_cents=-48900`, `total_cents=0` (a fully tax-credited
    invoice) — Podium's schema rejects a negative tax amount outright.
    That's a real, isolated source-data anomaly, not a platform bug:
    leave it as non-importable rather than guessing a "corrected" value
    (zeroing or flipping the sign would misrepresent the actual
    transaction).
- After upload, a "Parsed sheets — assign entity types" panel shows row/col
  counts (sanity-check against your source file) and an entity-type
  dropdown (`(auto-detect)` is normally fine). Click **Upload & Analyze**.

#### Step 2 — Mapping

AI pre-fills a **Target Field ↔ Source Column** table with a confidence
%, plus a one-line "Reasoning" per row. Required fields are marked `*`.

**Rule of thumb for what to flag (confirmed with the user):** treat any
mapping under ~90% confidence as suspect **unless** the source and target
column names are literally identical — an identical-name match is fine
regardless of confidence score, because the cleaning/scraping pipeline is
built so its column names already match the target schema. Don't just
trust the number in isolation.

**Verify against the actual source file, not just the on-screen
reasoning.** Read the CSV's header and a few sample rows yourself (`head`,
or a quick Python/pandas peek) before signing off on low-confidence rows —
e.g. confirm a date column really does carry a time component, confirm an
ID column is unique/non-empty, etc. Don't approve a mapping on vibes.

**Known entity-specific quirks** (documented so far for Job History —
expect other entities to have their own analogous quirks the first time
you upload them; verify against the real source data rather than
assuming, and add what you learn to this section):
- **Job History**: `start_time` / `end_time` target fields legitimately
  map to the **`job_start_date` / `job_end_date` source columns** (not a
  separate time column) at low confidence (~30%, reasoning "Assumed start
  time...") — this is *correct*, the system extracts the time component
  from the full ISO datetime. Confirm the source dates actually look like
  `2026-08-10T05:00:00` (have a time part) before approving.
- Some entities have **extra mapping sub-steps** after the main field
  table, each with their own confidence/no-match indicator and their own
  "Approve & Continue" (the last one reads "Approve & Preview"):
  - **Technician Mapping**: source technician string → Podium employee
    record. Only matches **single, exact names** — source values that are
    semicolon-combined multi-tech strings (e.g. `"Braden Naab; Austin
    Fontaine"`) show **0% / "— no match —"** and import with no
    technician assigned. This is normal/expected when the source data has
    combined names; per this shop's process it's left as-is (technician
    reconciliation happens later, working directly with the customer to
    get real techs set up in-app) — don't try to fix it here unless told
    otherwise.
    - **But not every 0%/no-match row is a real non-match — some are just
      small name mismatches** (e.g. source `"Reginald Lowe"` vs the
      Podium employee actually on file as `"Reggie Lowe"` — a nickname/
      formal-name variant the AI's exact-match logic doesn't catch).
      Click **"— no match —"** to open the "Map to technician" search —
      it's a real search box, not limited to the AI's own suggestions,
      and the right person often turns up immediately. Worth a quick
      manual check on single (non-semicolon-combined) names before
      accepting 0% as a genuine non-match, especially for names likely to
      recur across jobs (the shop owner, senior techs) where getting it
      right actually matters — don't burn time on this for names you'll
      never see again.
  - **Job Type Mapping**: source job types (e.g. Jobber's `RECURRING` /
    `ONE_OFF`) generally have **no Podium equivalent** and show 0%/no
    match — also expected/intentional to leave unmapped; those jobs
    import without a job-type assignment. **This only applies to
    internal recurrence/category tags, though** — if the source's job
    type column instead carries the FSM's real dispatchable work
    categories (e.g. ServiceTitan's own job types), 0%/no-match across
    the board almost always means the "Prerequisite" step above hasn't
    been done yet (Podium has no matching job types created), not that
    the source values are unmappable — go create them rather than
    accepting a wall of no-matches.
    - **Wizard quirk found once job types exist:** the suggestion engine
      normalizes whitespace/punctuation on the source's distinct values
      before generating rows, which can silently collapse two
      near-duplicate source job types (e.g. `"HVAC PM Service-Cooling"`
      vs `"HVAC PM Service - Cooling"`) into a single suggestion row and
      trip a blocking banner: *"N job types matched a name that exists
      under more than one business unit."* "Approve & Preview" stays
      disabled until every row flagged **REVIEW** is opened and its
      match manually confirmed via the "Map to job type" search (usually
      only one real candidate shows up) — this is quick, not a sign
      anything is actually wrong with the mapping.
  - **Estimate Status Mapping / Invoice Pay Status Mapping**: map each
    distinct source status string to one of Podium's fixed target
    statuses (estimates: `draft`/`sent`/`approved`/`rejected`-ish set;
    invoices: `draft`/`sent`/`paid`/`marked_as_paid`/`archived`, plus
    `— skip —` to leave unmapped). **Standing rule for this shop:** map
    by what the status *insinuates* about the document's real-world
    state, not just literal string similarity — e.g. source `"Pending
    Payment"` means the invoice was issued and is awaiting payment, so it
    maps to `sent`, not `— skip —` (the AI's default here was wrong and
    needs manual correction). Apply the same insinuation-based reasoning
    to whichever `draft`/`archived`/etc. values show up — voided/canceled
    → `archived`, not-yet-issued → `draft`, issued-and-outstanding →
    `sent`. **Confirmed edge case:** when the source has *both* an
    "Open" and a "Pending Payment" status, treat them as genuinely
    distinct states rather than collapsing them — "Open" stays `draft`
    (not-yet-sent) and "Pending Payment" is the `sent`/awaiting-payment
    state; don't assume "Open" also means sent just because it sounds
    similar; only shift a status off `draft` when the source vocabulary
    doesn't already have a separate value more clearly meaning "sent."
    **Confirmed for Jobber Estimates specifically: the actual valid-status
    dropdown only has 3 options — `draft`/`approved`/`rejected` — no
    `sent` at all**, unlike Invoices. The AI mapped every one of Jobber's
    4 source statuses to `draft` by default, which was wrong for the two
    that made up 98% of the account's estimates: `converted` (634 total,
    364 of them) means the customer accepted and it became a job/invoice
    → `approved`, not `draft`; `archived` (257) means declined/no longer
    valid → `rejected`, not `draft`. Only `awaiting_response` (sent,
    no decision yet) and literal `draft` correctly stay as `draft` — with
    no `sent` bucket available, "awaiting a response" has no better home
    in a 3-state model, so `draft` is the least-wrong choice there,
    unlike Invoices where a real `sent` option exists and should be used.
    **Always check the actual dropdown's option list before applying the
    Invoices-style reasoning** — the available target vocabulary differs
    per entity, and blindly porting one entity's status set onto another
    will misclassify almost everything if the target enum shapes differ
    this much.
  - **Membership Plan Mapping** (Memberships/Members entity): each
    distinct `membership_plan` value from the source needs to match an
    existing Podium plan record; rows with no match show 0% confidence
    and **"— no plan (bare account) —"**, with a warning that bare-account
    memberships may fail on import. There is **no way to create/upload the
    Membership Plans catalog through this same wizard** — "Memberships" is
    the only relevant Target Tables checkbox, there's no separate
    "Membership Plans" option, so if Podium doesn't already have the plan
    records (e.g. `cleaned-data/membership-plans.csv` hasn't been
    created/uploaded through some other path yet), every plan will show
    0%/bare-account regardless of how well the *name* matches. **When
    this happens, don't just accept bare-account and move on — flag it to
    the user** so they can get the plan records created/updated in Podium
    first (then a **"Refresh Plans"** button on this screen re-fetches
    current matches without restarting the wizard) — bare-account imports
    silently lose the plan association per membership, which is a real
    data loss, not a cosmetic gap.
  - **🎯 NEW (confirmed 2026-09-02, Paul's Heating & Air Conditioning /
    ServiceTitan): Lighthouse's Data Migration checklist has a built-in,
    non-CSV path for exactly this gap — "Set Up ___ with Operator."** Every
    checklist row's **Actions** dropdown carries a `Transform & Upload`
    entry regardless of whether that entity actually has a Target Tables
    checkbox in the wizard (Membership Plans and Estimate Templates both
    show it, but neither has a real Target Table — confirmed by opening the
    wizard's Target Tables list: only Memberships, Pricebooks, Job History,
    Contacts, Invoices, Estimates, Equipment exist. `Transform & Upload` on
    those two rows is a dead end — don't spend time trying to wire a CSV
    through it). **The row's second Actions entry is the real mechanism**:
    on the **Membership Plans** row it's `Set Up Memberships with
    Operator`; on the **Estimate Templates** row it's `Set Up Estimate
    Templates with Operator`. Clicking it opens a side panel: "Operator
    will set up the customer's [plans/estimate templates]. Attach [plan
    documents / example estimates, price sheets, template documents] —
    optional. Operator [figures out the plans, reconciles them against the
    members / drafts the templates], reaches out to the customer to fill
    any gaps, and shares a preview for approval before creating anything,"
    plus an **"Attach ... (Optional)"** file picker (Membership Plans also
    explicitly accepts a member list as CSV/XLSX here — our own scraped
    `raw/<Customer>_Members.csv` is exactly what it's asking for) and a
    **"Choose Enrolled Operator"** search box (options seen: a generic
    "Podium Operator" account, plus the customer's own enrolled staff —
    e.g. Evan Rasmussen, Mitch Schneider), then a **"Start Setup"** button.
    **⚠️ `Start Setup` triggers real outreach to the customer** ("reaches
    out to the customer to fill any gaps") — this is a customer-facing
    action, not a local data transform, so per this skill's caution
    section it needs the user's explicit go-ahead each time, the same as
    sending any other message on the customer's behalf. Don't click it on
    your own judgment just because the panel is open and ready. Surface
    what you found (which documents you'd attach, which operator makes
    sense) and let the user decide whether/when to kick it off. **This is
    now the standard path for both Membership Plans and Estimate
    Templates** — for Estimate Templates specifically, there is no
    documented manual-build-via-Mock alternative the way Membership Plans
    has (see below), so this Operator flow is the *only* known path for
    that entity; treat "Set Up Estimate Templates with Operator" as a
    standing checklist item for every ServiceTitan (and likely other FSM)
    migration going forward, not an edge case.
  - **Building the Membership Plans catalog in Podium from the source
    FSM's own membership-type config (since the wizard can't create it —
    see above)** — the manual/Mock-based alternative to the Operator flow
    above, useful when you'd rather build the plans yourself than route
    through Operator (e.g. a small, well-understood plan catalog). For
    ServiceTitan specifically, the source data lives at
    **Settings (top-right gear) → Invoicing → Membership Types** — this
    list is the authoritative catalog (confirmed via its own pagination
    footer, e.g. "1 - 12 of 12 items"; don't assume a raw scrape's count
    of distinct `membership_plan` strings from job history matches this —
    a job-history scrape can carry many more distinct *names* than the
    FSM's current Membership Types config actually has, since history
    spans renamed/retired plans that never got cleaned up). **For
    HouseCall Pro specifically:** the authoritative catalog is at **My
    Apps (the 3×3 grid icon in the top nav) → Service plans → "Plan
    templates" panel** on the left of the Service Plans dashboard (this
    is HCP's "Plans We Offer" — the templates, not the individual member
    agreements). **Click each template** to open its detail page, which
    shows visits/year, duration ("continues until canceled" = indefinite,
    or "N year in duration"), plan cost + billing frequency ("$X every
    month", and the raw `Plans` scrape sheet's `payment_options` column
    also lists a yearly price if one is offered), the discount %, the
    add-on / "additional system" price, and the full member-facing
    description + benefits list. Confirmed on Today Air: HCP's Plan
    templates panel showed exactly the 2 templates the `Plans` scrape
    sheet had, and a 3rd name ("Family Comfort Club") that appeared only
    on old member agreements was a **retired rename** of an existing
    template, not its own template — treat a job/membership-history-only
    plan name as retired (route those members to
    `members-non-importable.csv`, see the split rule below), don't invent
    a template for it. Then **build the equivalent plan(s) in
    Podium via Mock** (Lighthouse hamburger ☰ → "Open Organization in
    Admin" → admin.podium.com → **Mock** button, confirm the yellow
    "Mocked in as [name]" banner and the correct account name before
    proceeding) → **Memberships tab → Plans → "Create plan" / "New
    plan"**. The 4-step create flow is **Plan (name + tier name) →
    Billing (Price; Extra System Price; Period Monthly/Yearly; Renewal) →
    Benefits ("Add discount" → Percent Off + Applies To "All services")
    → Review (auto-generated Description + Terms; paste the real
    HCP description over the default)**. **Monthly + yearly of the same
    program:** after saving the monthly plan, its Plans-page card has a
    **"+ Add yearly option"** link — use that (it pre-fills a linked
    yearly plan named "<name> Yearly" with price = 12× the monthly;
    override the price to the real annual figure and the extra-system
    price to 12× monthly). This supersedes the older "always two
    fully separate plans" note below for FSMs whose UI offers the
    add-option link — you still get two plan records, but linked as one
    program with a monthly/yearly toggle on the card. A **$0 plan**
    (e.g. HCP's "…New Install" one-time plan) is forced to Manual
    renewal by Podium ("Auto-renewing plans need a price greater than
    $0") and its Extra System Price should be left blank, not "0".
    Verify a saved plan's real stored price via **Edit plan** — the
    Plans-page summary rounds ($14.99 shows as "$15/mo").
  - **⚠️ Set every built plan's Renewal to "Manual renewal," not
    "Auto-renew" (the wizard's own default), unless you are also
    migrating real credit-card/payment-method data for these members —
    which a historical CSV import never has.** Confirmed the hard way
    across four separate Members upload attempts on one migration: a
    plan built as Auto-renew makes Podium's Members import **reject
    every single row** with `"Auto-renewal is required for this plan"`
    (`code: missing_required`) — and this is not a CSV-encoding problem.
    All three plausible encodings of the CSV's `is_auto_renewal` column
    were tried and every one failed identically: blank, the English word
    `"No"`, and even the literal lowercase boolean-string token
    `"false"` that the field's own description asks for
    ("Whether the membership auto-renews (true/false)"). The plan-level
    Auto-renew setting apparently requires `is_auto_renewal=true` (i.e.
    a real payment method to bill against) full stop — it will not
    accept an explicit `false` override. **The fix:** edit each plan
    (Memberships → Plans → select tier → **Edit plan** → Billing section
    → Renewal dropdown → **Manual renewal** → Save changes; do this for
    every tier of every plan, since Renewal is set per plan-*tier* row
    even though cadence is shared per plan) before the first Members
    upload attempt, then leave `is_auto_renewal=false` in the CSV (still
    the only truthful value for migrated data with no real payment
    method attached — not a guess). This is safe to do even after a plan
    already has real members on it: the confirmation dialog explicitly
    states the plan-definition edit does not add/remove/reset vouchers
    already issued to existing members. If you only discover this after
    a failed upload, no data is lost — fix the plans, then use the
    failed session's own **"Retry Upload to FSM"** button (Review step)
    rather than starting a new session; rows that succeed on retry show
    up as new `Created` count, and rows that already succeeded in an
    earlier partial attempt correctly show `Duplicate enrollment` rather
    than failing again — that's expected, not a new problem, and doesn't
    need re-diagnosing.
  - **⚠️ Fixing the plan to Manual renewal doesn't protect against a
    single row whose own `is_auto_renewal` value is `true`** — confirmed
    on Today Air: 11 of 12 members imported cleanly on a Manual-renewal
    plan with `is_auto_renewal=false`, but the 12th failed with the exact
    same `"Payment account is required for auto-renewal members"` error
    even though the plan itself was correctly set to Manual. Cause: that
    one row's source data (HouseCall Pro) genuinely had
    `is_auto_renewal: true` recorded on it, unlike every sibling row —
    Podium honors the *row's* flag, not just the plan's renewal setting,
    so a `true` row against a real-payment-required plan fails no matter
    how the plan is configured. **Fix, same reasoning as the plan-level
    case above:** correct that row's `is_auto_renewal` to `false` in
    `cleaned-data/members.csv` (migrated data never has a real payment
    method regardless of what the source recorded — `false` is the
    truthful value here too, not a guess), then re-upload just that row
    through a fresh Transform & Upload session (**Start Over** first if
    the wizard tries to resume the prior failed session — see the
    "Resuming vs fresh session" note above). Check every members row's
    `is_auto_renewal` value before the first upload attempt, not just the
    plan-level setting, to catch this in one pass instead of a retry.
  - **Two ways a source membership type can be legitimately
    non-importable — flag both to the user rather than guessing a fix:**
    - **No price configured at all.** A membership type can have a fully
      valid name, discount table, and recurrences, but its Billing
      Template is simply empty — no billing template row, no flat price,
      `Total` never rendered. This isn't a scrape/read error (confirmed
      by re-reading the page after a wait); it's a genuinely incomplete
      configuration in the source FSM. Don't invent a price (e.g. don't
      assume "yearly = 12× the monthly sibling's price" even when a
      monthly sibling exists with the same name pattern) — file it as
      non-importable and note the gap for the user.
    - **Test records and empty shells mixed into the real list.** Not
      every row in the source's membership-types config is a real,
      customer-facing plan — watch for: a name/tag containing "Test"
      (e.g. `WSSP-BFA-Test-Dr Garner`), multiple simultaneous
      billing-cadence configs on one record (a real plan has exactly
      one), or a row with **zero everything** (0% discount, no billing
      template, no recurrences, often defaulted to "All Locations"
      instead of the single location every real plan uses) — these are
      staff sandbox/placeholder records, not plans to recreate in Podium.
      Also watch for a real, actively-used recurring *service program*
      (e.g. an annual backflow-device test) that nonetheless has **no
      flat membership price** because it's priced per individual sale
      task at time of service rather than as a subscription fee — this
      doesn't map cleanly to Podium's flat-price-per-tier model either;
      flag it rather than forcing a price.
    File every one of these (missing-price and test/shell/no-fixed-price
    alike) the same way non-importable rows from any other entity are
    handled: preserved with a reason, not silently dropped, and surfaced
    to the user — including in the migration exceptions report (see
    Phase 4 below) as a `membership_types` (or similarly named) entity
    alongside the row-level non-importable tables for Jobs/Contacts/
    Pricebook/etc., so the customer/CSM can see exactly which source
    membership types didn't make it into Podium and why.
  - **Confirmed on Members specifically: the "history outlives current
    config" split can be large — clean the Members CSV, then check how
    many rows survive against the built plans *before* touching the
    wizard.** On one migration, the source Members export referenced 37
    distinct `membership_plan` strings while ServiceTitan's *current*
    Membership Types config only had 12 (and only 7 of those were real,
    per the judgment calls above) — 1,145 of 1,543 rows (74%) matched a
    built plan cleanly, the other 398 (26%) referenced ~30 retired/
    one-off historical names with no live Podium plan to attach to.
    Rather than upload all 1,543 in one pass and accept ~400 silent
    bare-account matches (or worse, guess which retired name maps to
    which current plan), **split the cleaned CSV in two before ever
    opening the wizard**: `members.csv` = only rows whose
    `membership_plan` matches a built plan name exactly (normalize
    whitespace only, don't fuzzy-match), `members-non-importable.csv` =
    everything else, held for the user's decision. Upload just the
    matched file — this is real, safe progress (real members with real
    plan links) that doesn't depend on the ambiguous 26%, and it doesn't
    leave a half-confirmed Plan Mapping screen sitting open. Verify at
    the wizard's own Membership Plan Mapping sub-step that every
    remaining distinct plan name shows a real match (not bare-account)
    before approving — if the split was done right, this step should
    show 100% real matches, confirming the split logic actually worked
    rather than just hoping it did.
  - **⚠️ Wizard can silently auto-advance past a sub-mapping step —
    verify you actually reached Review deliberately, not by accident.**
    Confirmed in practice: interacting with a sub-mapping dropdown (e.g.
    clicking a "no plan (bare account)" selector) was immediately followed
    by the wizard already sitting on **Step 5/Review with Transform shown
    complete**, despite never clicking that sub-step's own "Approve &
    Continue" nor Preview's "Run Full Transformation." The exact trigger
    wasn't isolated. **Treat an unexplained jump to Review as a signal to
    stop and verify, not to proceed** — use **"Back to Mappings"** (or
    re-open the sub-step) to confirm what was actually submitted before
    touching Upload to FSM; don't trust Review's stats alone (they can
    reflect a genuinely-good transform even after a confusing navigation
    path, but confirm rather than assume).
- Click through each mapping/sub-mapping table's **Approve & Continue**
  (or **Approve & Preview** on the last one) once reviewed.

#### Step 3 — Preview

Shows the first 5 transformed rows per sheet. **Yellow cells = the system
auto-corrected that value** (e.g. `"Texas"` → `"TX"`) — scroll right to
check every column, since auto-corrections aren't always in the first
visible columns. If it all looks sane, click **Run Full Transformation**.

#### Step 4 — Transform

Runs automatically after clicking "Run Full Transformation" — no
interaction needed, just wait a few seconds; it lands you on Review.

#### Step 5 — Review

**In bulk mode (multiple entities uploaded together), Review has one tab
per sheet (e.g. "Jobs / Invoices / Estimates") each with its own header
stats, row table, and its own "Upload to FSM" button.** ⚠️ **Check every
tab before uploading anything** — it's easy to review the first tab, look
fine, and click Upload to FSM without ever seeing that a later tab has a
real problem. Click through All rows / Errors only / Warnings only on
*each* tab, not just the one that happened to load first.

**⚠️ If any one sheet in a bulk-mode session turns out to have a real
problem (e.g. the ID sanity check below fails), don't click Upload to FSM
on the other, clean tabs either — per the user's explicit call, treat the
whole session as tainted and Start Over.** Confirmed in practice:
per-tab upload buttons are *not* treated as safe to cherry-pick from once
one sheet in the batch is known-bad, even though each tab visually looks
independent. Start a fresh Upload step selecting only the Target Tables
that are actually clean (e.g. drop Estimates from the Target Tables
multi-select, keep Job History + Invoices), rather than trying to salvage
a mixed session.

**⚠️ ID sanity check — do this on every entity with an external/foreign
ID column before uploading, not just when something looks obviously
wrong:** a legitimate external ID (job #, invoice #, estimate #, etc.)
from these FSMs is a **short human-readable number, roughly 0-8 digits**
(e.g. job `9055`, invoice `9026`) — that's the number visible in the
FSM's own UI and on the customer-facing document. **If an ID column
instead contains a long internal-API string** (e.g.
`est_ea7ee7791a2e4447986b2cb32e81df18`) **that's a scraper bug, not a
data-quality quirk to route around** — it means the scraper's field
mapping grabbed the FSM's internal database UUID instead of the
human-readable number for that specific entity (confirmed case: Job IDs
and Invoice IDs came through correctly as short numbers, but Estimate
IDs came through as raw HCP UUIDs — an entity-specific bug, not an
account-wide one). **Do not upload that entity's data as-is** — flag it
to the user immediately, don't try to reformat/truncate the bad ID
yourself, and expect the fix to be either a corrected/updated scraper
(the user may already have one) or a rescrape of just that entity once
fixed. Entities with good IDs can still proceed on their own schedule —
this doesn't have to block the whole migration, just the affected
entity.

**🚨 CRITICAL, distinct failure mode confirmed for Jobber (not a scraper
bug this time — a Phase 2 cleaning-script bug): the raw scrape can have
BOTH the correct short ID and the long internal-API ID as two separate
columns, and the cleaning step mapped the wrong one.** Caught at the
Preview screen (step 3) on an Invoices upload — `external_id` showed
values like `MTY3OTMyODM3` (Jobber's base64-ish internal invoice ID)
instead of the real invoice number. The raw `MLD Services_invoices.csv`
export actually had **both** `external_id` (the internal ID, wrong) and
`invoice_number` (the real short number, e.g. `24567`, right) as
separate columns — the cleaning script's `external_id` mapping just
picked the wrong one. **Same bug, same shape, in Estimates**: raw
`external_estimate_id` is the long internal ID; raw `quote_number` is
the real short number — `estimates.csv`'s `external_estimate_id` column
must be built from `quote_number`, not from `external_estimate_id`.
**Do this check on every entity before Upload, not just when Preview
already looks wrong**: open the raw CSV yourself and confirm which
column is the human-facing number *before* trusting whatever the
cleaning script mapped — a plausible-sounding column name (`external_id`
matching the target field name) is not proof it's the right value, since
the source can have a same-shaped decoy column sitting right next to the
real one. Verify uniqueness (no duplicates, no blanks) on whichever
column you pick before using it — confirmed clean (4,239/4,239 unique
`invoice_number`, 634/634 unique `quote_number`) in the case that
surfaced this, but don't assume that holds for every account without
checking.

**🚨 Another failure mode the Preview screen does NOT catch: `line_items_json` money fields as dollar strings instead of integers.**
Confirmed on Invoices: Preview (step 3) showed a clean 90% score, 0
errors, 0 warnings — looked fine — but clicking Upload to FSM on the
full 4,236-row file came back **"Upload failed — all rows had
errors," 4,236/4,236 failed**, every single one with the identical
reason `line_items.0.unit_price: must be a integer; line_items.0.unit_cost:
must be a integer` (and `.1.`, `.2.`, etc. for multi-line invoices) — the
scraper had emitted `"unit_price": "$25.00"` instead of an integer cents
value, and nothing before the actual upload attempt surfaced it. If an
entity's line items carry money fields, verify their JSON-encoded type
(integer cents, not a dollar string) in `cleaned-data/` yourself before
uploading a large file — don't rely on Preview being clean as proof the
full upload will succeed for nested/JSON fields, only for the flat
column-level checks it actually performs. If you do hit a 100%-failure
upload, download the error report immediately (per "Triaging failures"
below) — a uniform failure reason across every row like this is a single
cleaning bug worth fixing and re-uploading whole, not a per-row triage
problem.

Header stats: **Overall Score**, Completeness %, Format Validity %, Rows
Needing Review. Tabs filter the row table: **All rows / Needs review /
Errors only / Warnings only** (each shows its count as a badge).

Click **"Color Guide [swatches] show"** to expand the legend (worth doing
once per session rather than guessing from color):
- **Row colors**: red row = missing a required field (or, for contacts,
  missing both phone and email); yellow row = a format issue (phone,
  email, or date format).
- **Cell border (left pipe)**: red pipe = that specific cell is the
  problem field; yellow pipe = that cell has a format warning. **Hover
  the cell** (not click) to get a tooltip with the exact reason (e.g.
  `"Invalid datetime: 2026-08-07"`, `"Incomplete address"`).
- **Score %**: ≥85 green, 70–84 yellow, <70 red.

**⚠️ Important rule from the user, confirmed explicitly:** only rows in
**"Errors only" must be fixed and/or moved to the non-importable file**
before uploading. Rows that only show up under "Warnings only" are fine
to upload as-is — don't hold up the upload trying to resolve every
warning. (In practice, Warnings-only rows are often expected quirks like
the technician/job-type non-matches above, or date-only source values
producing an "assumed time" — not blockers.)

Wide tables here need **horizontal scrolling** (`computer` action
`scroll`, `scroll_direction: "left"/"right"`) to see all columns —
content doesn't reflow to fit the viewport. The grid also appears to be
virtualized/canvas-based: **DOM `querySelector`/text-search via
`javascript_tool` does not reliably find rendered cell content** even for
visible rows — rely on screenshots + `hover` + tooltip reads instead, not
scripted DOM scraping.

When ready, click **Upload to FSM** to kick off the real import.

### The actual upload

After clicking Upload to FSM, the button shows "Uploading..." and an
**"Import progress"** panel appears with a live counter
(`825 / 2,526 · 20 failed`, polling upward) — `wait` a few seconds and
re-screenshot repeatedly until it reaches "N of N complete" / status
`DONE`, `DONE WITH ERRORS`, or `FAILED`.

- **`FAILED` / `DONE WITH ERRORS`**: a red/orange toast appears
  ("Import failed" or "Import completed with errors"), and new buttons
  show up: **View row outcomes**, **Download error reports**, **Retry
  Upload to FSM**, alongside Download Transformed File / Approve Sheet.
  - **View row outcomes** opens a panel with **Failures / Skipped / All**
    tabs listing each failed row's `Row` (CSV row number, 1 = header),
    `Status`, `Code` (e.g. `IMPORT_ERROR`), and `Message` — use this to
    confirm exactly which rows succeeded vs. failed after a retry (the
    row numbers you *don't* see under Failures are the ones that made it).
  - **Retry Upload to FSM** vs plain **Upload to FSM**: if you resumed an
    already-failed session (see the "Resuming" warning above) and click
    the plain "Upload to FSM" button, it errors with `{"error":"GraphQL
    error: Import cannot be triggered: import_status is already failed"}`
    — use **"Retry Upload to FSM"** instead in that case.
- **`DONE`** (clean success): no error buttons appear, just Download
  Transformed File / Approve Sheet.

### ⚠️ Critical: Job History import is insert-only — it does NOT upsert by `job_id`

**Confirmed 2026-08-14 on the MLD Services / Jobber migration.** Every
successful Job History upload's "View row outcomes" / Summary panel
(accessible from the Data Migration tab's **History** view → a row's
**Summary** link → "Import outcomes") reports a **Created** / **Updated**
/ **Failed** / **Excluded** breakdown. Checked across every Job History
upload attempt on this account (Aug 6, Aug 6, Aug 13, Aug 13, Aug 14,
Aug 14) — **`Updated` was 0 on every single one**, no matter how many
`job_id`s in that file also existed from an earlier successful upload.
Every successful row is inserted as a **brand-new job record**, never
matched against an existing one by `job_id` (or anything else).

**Practical consequence: re-uploading a `jobs.csv` with corrected dates
to fix previously-wrong job records does not fix them — it creates a
second, duplicate job record with the correct data, while the original
wrong-date record from the earlier bad upload is left untouched and
still live in the product.** This is why a date-correction pass can
report a clean "2,343 success / 0 failed" in the wizard while the
customer/user still sees wrong times when looking at jobs in the actual
product — they may well be looking at (or the UI may be surfacing) the
stale duplicate from an earlier attempt, not the freshly corrected one.
Symptom to watch for: the checklist's **In Product** count for Job
History being noticeably higher than the row count of the file you just
uploaded (e.g. 2,493 in product vs. 2,343 rows in the latest correct
file) — that gap is leftover duplicate/orphaned records from earlier
attempts, not new legitimate jobs.

**Before doing a corrective re-upload of Job History (or trusting that
one already happened), check every prior Job History upload's Import
outcomes panel for nonzero `Created` counts, and treat every one of
those as still live in the product with whatever data it had at the
time — the newest upload does not supersede them.** If a customer's data
has gone through multiple correction passes, the accumulated duplicate
count can be large. This skill does not yet have a confirmed way to
delete/merge the stale duplicates from inside Lighthouse or the mocked
product view — **pause and ask the user how they want to handle existing
duplicates** before uploading another corrective pass, rather than
assuming a clean re-upload will resolve what's already live.

### Investigating directly in the customer's Podium account

For failures the error-report CSVs alone can't explain (e.g. a generic
`upsert_contact failed: unknown error`, or an `identifier conflict` where
it's unclear whether the conflicting identifier is duplicated within your
own file or already split across two pre-existing Rolodex contacts — see
the "third source" case above), **log into the customer's actual Podium
product account and search their live Contacts/Accounts directly** rather
than guessing from the CSVs alone:

1. On the Lighthouse location page, click the **hamburger menu (☰)** at
   the top right, next to the clock/timezone display.
2. Click **"Open Organization in Admin"** — opens `admin.podium.com` for
   that org in a new tab.
3. On the admin org page, click **"Mock"** at the top right (**not**
   "Support Mock" — that's a different, separately-logged tool; use plain
   Mock) — opens a new tab logged into the customer's actual
   `app.podium.com` product account (a yellow "Mocked in as ..." banner
   confirms it, with a **Sign out** button).
4. Use the left sidebar's **Contacts** tab to search by name, phone, or
   email and inspect exactly what's already on file (existing
   phone/email/property/notes) for a specific person. There's also an
   **Accounts** tab specifically for looking up accounts that have
   multiple properties associated with them (e.g. property-management/
   multi-location customers) — useful for the same over-merge patterns
   Phase 2's anti-merge rules watch for.
5. This is read-only investigation — don't edit the mocked account's data
   directly; make any fixes back in `cleaned-data/` and re-upload through
   the normal wizard instead, so the change stays reproducible and
   visible in the migration's own history.

This was the deciding technique for the "third source" identifier-conflict
case above: the CSVs alone couldn't show that "Meagan Rose"'s phone and
"Ethan Glenn"'s email had already been correctly split into two separate
existing contacts — only searching the live account surfaced that.

### Triaging failures: error reports, reconcilable vs. non-importable

This is the core judgment-call workflow — don't skip the analysis.

1. **Download the error report.** Click **Download error reports** → it
   saves a CSV to `~/Downloads/` named like
   `<org-uid>-failed-<entity>.csv` with columns `_csv_row_number,
   <entity>_number, ..., reason`. Immediately move it into a fresh, timestamped
   subfolder so repeated attempts don't overwrite each other:
   ```
   TS=$(date +"%Y-%m-%d_%H-%M-%S")
   mkdir -p ~/Downloads/failures-$TS
   mv ~/Downloads/<the-file>.csv ~/Downloads/failures-$TS/
   ```
2. **Categorize each failure reason** (group by the `reason` text — e.g.
   `"Customer could not be matched. Provide at least one of:
   customer_email, customer_phone, or customer_name."` vs `"Multiple
   customers matched the provided name..."` vs an address/date-format
   message).
   - **Contacts can produce *two* error-report files from one upload** —
     `<org-uid>-failed-contacts.csv` (columns: `reason, row_index` only)
     and `<org-uid>-failed-contact_property_post_stage.csv` (full row data
     + `error`), reflecting two internal import phases (creating/matching
     the base Contact, then updating its Property). **Check for row_index
     overlap between the two before adding their counts** — in practice
     the property-stage failures were a strict subset of the contact-stage
     ones (same underlying row failing at both stages), so the true unique
     failure count was the *larger* file's count, not the sum.
   - **`"identifier conflict: row identifiers resolve to different
     Rolodex contacts"` / `"...phone and email resolve to different
     Rolodex contacts"`**: Podium's own contact-matching (Rolodex) found
     the row's phone attached to one existing contact and its email
     attached to a *different* existing contact, so it can't resolve
     which to update. Two distinct sources for this, requiring different
     handling:
     - **Self-inflicted (reconcilable — fix and re-upload):** the
       *uploaded file itself* has the same email (or phone) spread across
       multiple rows with different phones (or emails) — e.g. a
       property-management contact whose duplicate HCP records got left
       as separate rows (see Phase 2's property-manager anti-merge note)
       each keeping the same shared email. Verify by checking your own
       `cleaned-data/<entity>.csv` for the failing rows' phone/email
       appearing more than once with a differing counterpart value. Fix:
       keep the identifier on one canonical row per conflicting group,
       blank it on the rest, re-upload.
     - **Pre-existing in Podium (not reconcilable via re-upload):** if the
       failing rows' phone/email are *not* duplicated within your own
       file, the conflict is between two already-existing Rolodex
       contacts from prior data (an earlier upload, manual entry) — no
       amount of re-uploading the same clean row fixes it, since the
       ambiguity lives on Podium's side. Treat as non-importable for this
       cycle (append to `<entity>-non-importable.csv`) and flag it as
       needing manual Rolodex cleanup in Podium — **per the skill-wide
       judgment-call rule, this classification is a guess based on
       inference (absence from your own file), not a deterministic
       signal, so confirm it with the user every time before filing any
       rows away this way, not just the first few times or only for
       large batches.**
     - **Third source (reconcilable, but the fix is in Phase 2, not in
       re-uploading as-is): a Phase 2 cleaning-stage merge bug that
       cross-wired two different real people's identifiers onto one
       row.** Distinguishing this from the two cases above requires
       actually looking at Podium's live Rolodex (see "Investigating
       directly in the customer's Podium account" above) — it looks like
       neither a same-file duplicate nor a pure pre-existing-data
       collision from the CSVs alone. Confirmed pattern: the source FSM's
       raw contact record represented a *household of 2+ people* (e.g. a
       couple) as one client with multiple phones/emails; the cleaning
       step's "first phone + first email" primary-selection picked one
       person's phone paired with the *other* person's email (the raw
       arrays aren't guaranteed to be index-aligned per-person). Podium's
       Rolodex had *already* correctly resolved these as two separate
       existing contacts (e.g. "Meagan Rose" `(512) 296-8480` /
       `meagank.rose@gmail.com` and "Ethan Glenn" `(832) 797-2084` /
       `ethan.glenn84@gmail.com` as two distinct contacts) from an earlier
       upload — the mismatched row was trying to write Meagan's phone
       with Ethan's email, hence the conflict. **Fix:** look up each
       conflicting row's phone and email separately in the live Podium
       Contacts search; whichever identifier's existing contact *name*
       matches the row's own `first_name`/`last_name` is the correct one
       to keep — drop the other identifier from the primary field (fold
       it into `contact_notes` instead, e.g. "Additional [phone/email],
       may belong to another household member: ..."), then re-upload just
       that row. Don't guess which identifier is "right" from the CSV
       alone — the whole point of this case is that the file's own data
       doesn't reveal the mismatch; only the existing Rolodex does.
3. **Cross-reference against source data before deciding anything.** For
   each failed row's ID, look it up in:
   - `cleaned-data/<entity>.csv` (what was actually uploaded) — does it really
     lack the field the error complains about?
   - `raw/<Customer Name>_<entity>.csv` (pre-cleaning scrape output) — is
     the field *also* missing there, or did the cleaning step accidentally
     drop something recoverable? If raw has it and cleaned doesn't,
     that's a cleaning bug, not missing data.
   - The corresponding **contacts/customers file** — does the referenced
     customer actually exist there with valid contact info, and are they
     *also absent* from `<entity>-non-importable.csv`? If they exist
     fine on the customer side, the failure is likely upstream (see the
     "job-matching needs a working Contact" lesson below), not a data gap
     in the failed file itself.
4. **Classify each row:**
   - **Reconcilable** — the data needed to fix it genuinely exists
     somewhere accessible (source file, or an upstream entity just needs
     fixing/retrying first). → goes in a `reupload/<entity>.csv` staging
     file, **unedited**, for retry.
   - **Truly non-importable** — confirmed missing/ambiguous even in the
     raw scrape (e.g. Jobber itself never captured an email or phone for
     that customer; or only a bare first name like "Johnson" matches
     multiple contacts with no way to disambiguate). Needs either the
     customer to supply info or someone to make a manual judgment call.
     → **append** these rows (matching `<entity>.csv`'s exact column
     schema — no extra `reason` column) to
     `cleaned-data/<entity>-non-importable.csv`.

#### Key lesson: "reconcilable" isn't the same as "will succeed on retry"

**This generalizes beyond Job History to any entity with a foreign-key
dependency on another entity** (Job History → Contacts; Invoices/
Estimates → Contacts *and* Job History; etc., per the upload-order table
above). A row can only import if the record(s) it references already
exist as **successfully-imported** records in Podium — having valid
linking fields (`customer_email`/`customer_phone`, `job_id`, ...) in the
*current* entity's source data is necessary but **not sufficient**. If
the referenced upstream record itself failed during its own import
(visible as "N success · M failed" on that entity's checklist row), every
downstream row referencing it will keep failing with the same
"could not be matched"/"not found" error **even after you re-upload the
identical downstream data unchanged** — re-uploading the same file
changes nothing on its own.

The fix is to go **fix the upstream entity first** (re-run/retry its
specific failed rows — e.g. via `Actions → Transform & Upload` on the
Contacts row, uploading whatever data is actually new/available, such as
a `cleaned-data/new-since-8-6/customers.csv` delta from a recent rescrape),
**then** retry the downstream upload. Confirm the upstream fix actually
covers the record you need before assuming it'll fix a given failure —
checking a customer's/job's identifying info against the delta file is a
30-second `grep` that saves a wasted retry cycle.

After retrying with everything currently available, **rows that still
fail with the same reason are now proven non-importable for this cycle**
— move them from `reupload/` into `<entity>-non-importable.csv` and
delete/clear the now-consumed `reupload/<entity>.csv`. Use **View row
outcomes** after a retry to see precisely which of the retried rows
succeeded vs. still failed (see above).

#### Matching failed rows back to `cleaned-data/<entity>.csv` when the error report has no row-number column

Some error reports carry a row identifier (`_csv_row_number`, `row_index`)
you can join on directly — trust that over any other matching approach.
**Others (confirmed for Memberships) carry no row identifier at all, just
the full failed row's data plus a `reason` column** — you have to match
back to `cleaned-data/<entity>.csv` by content.

**Match on every column the error report provides, not a partial key.**
Picking a "should be unique enough" subset (e.g. name + plan + start_date)
breaks silently when the source data contains legitimate near-duplicate
rows that differ only in a field you left out of the key — e.g. two
membership rows for the same person/plan/start_date that differ in
`is_auto_renewal`/`end_date` (one an original enrollment, one a later
renewal). A partial-key match can match the *wrong* one of the two,
wrongly moving a row that never actually failed into
`-non-importable.csv` while leaving the real failure behind. Confirmed
case: matching on `(contact_name, membership_plan, phone, start_date)`
alone moved a Luke Roberts row with `is_auto_renewal=Yes` into
non-importable, when the actual Lighthouse failure was the *other* Luke
Roberts row (`is_auto_renewal=No`) — caught by re-tallying counts: 15
rows moved for what the error report said were only 14 failures. Also
normalize formatting differences before matching (e.g. phone
`"(706) 506-3635"` in the error report vs `"7065063635"` in
`cleaned-data/`, via `re.sub(r'\D', '', phone)`).

**After matching, sanity-check the counts, not just that matching
"worked":** the number of rows moved into `-non-importable.csv` must
equal the error report's row count *exactly*. If it doesn't, don't just
accept the mismatch — tabulate both sides by the same key and diff them
to find the specific row(s) responsible before moving on.

#### Related but distinct: "job not found" can mean the job never existed in the scrape at all, not just that it failed to import

A `"job not found for job_id 'N'"` error on Invoices/Estimates has **two
different root causes that require the same triage step to
distinguish** — always check both:
1. The referenced job is in `jobs.csv` but failed its own import this
   cycle (the "upstream dependency" case above — reconcilable by fixing
   Job History first).
2. **The referenced job_id doesn't exist in `jobs.csv` *or*
   `jobs-non-importable.csv` at all** — it was never in the source
   scrape to begin with. Confirmed case: 919 of 1,402 unique missing
   job_ids referenced by failed invoices were absent from the entire
   Jobs export (8,046 scraped jobs, fully accounted for between
   `jobs.csv` + `jobs-non-importable.csv`). This means the FSM's Jobs API
   simply doesn't return these jobs anymore (most likely deleted/purged
   from the source system over time) even though older Invoice/Estimate
   records still carry the old job_id reference. **This is not a scraper
   bug and not fixable by rescraping** — the data is gone at the source.
   Treat these as non-importable immediately, no retry cycle needed.

Distinguish the two with one `grep`/set-membership check per failure
batch: pull the unique missing job_ids from the error report and check
membership against `jobs.csv` ∪ `jobs-non-importable.csv`. IDs present in
neither are case 2 (source-data gap, file as non-importable straight
away); IDs present in `jobs-non-importable.csv` specifically confirm case
1 for that row. Don't assume every "not found" is the retriable upstream
case — at this shop's actual failure volumes, the source-gone case was
the overwhelming majority (~1,424 of 1,430 invoice failures), not the
minority.

#### A third classification, distinct from reconcilable/non-importable: "already correct in Podium, re-upload was never going to succeed by design"

Not every failure means something is wrong with the data — some mean the
**row doesn't need fixing at all** because it already imported
successfully in an earlier cycle, and Podium is correctly refusing to
let a bulk re-import silently overwrite fields on an already-finalized
record. Confirmed on Invoices: re-uploading a full 4,236-row file (most
of which had already been imported successfully in an earlier session —
checklist showed Invoices already `COMPLETED`, 3,985 in product) came
back with the overwhelming majority of "failures" reading `"Completed
Oceans invoice imports can only update line_items and derived amounts;
unsupported invoice-level changes: notes"` (and combinations with
`job_uid`, `issue_date`, `due_date`, `customer_uid`) — **4,155 of 4,225
failures**, vs. only 70 with a genuine data problem (`line_items[0]:
quantity must be positive`, from real `quantity: 0` line items in the
source) and 11 that were actually new and imported cleanly.

**What this means:** once an invoice/estimate reaches a terminal state
(paid, completed, etc.) in Podium, re-importing the same external_id
can only touch line items and the amounts derived from them — it will
never accept changes to notes, dates, or the linked job/customer, even
if your freshly-cleaned file has "better" values for those fields now.
This is Podium protecting financial records that have already been
finalized, not a bug to route around.

**Triage accordingly:** don't keep retrying a batch dominated by this
reason — retrying changes nothing, since the rule is permanent, not a
transient state. Treat rows failing with this exact message as **already
successfully represented in Podium** (from whichever earlier cycle
created them) — no further action needed, don't file them as
non-importable either (they're not missing, they're just locked). Only
chase the genuinely different failure reasons in the same batch (here,
the 70 zero-quantity rows) as real triage work. If you're not sure
whether a large uniform-reason batch like this represents "already fine"
vs. a real problem, the phrase to watch for is "can only update
line_items and derived amounts" (or similar "locked/completed record"
language) — that's the tell that re-upload was never going to succeed
here by design, regardless of how correct your cleaned data is.

### The rescrape decision

Per this shop's process: a **full rescrape is a last resort**, not a
first move. It only happens **after** you've gone through the *entire*
entity sequence — contacts through invoices (all target-table types) —
uploading everything currently available, retrying what's reconcilable,
and filing everything else into the `-non-importable` files. Only once
that full audit is done, and the non-importable files represent genuine
gaps, do you rescrape the customer from source (**without attachments**)
to see if fresh data closes those gaps. Don't suggest a rescrape as a
first response to a handful of failed rows — that's what the
non-importable triage above is for.

## Phase 3b — Job Attachments (only when explicitly requested)

A completely separate pipeline from everything above — different
scraper, different upload mechanism, no CSV cleaning step, and it does
**not** go through the FSM Data Transformer wizard covered in Phase 3
above. Only run this when the user explicitly asks for job attachments
specifically (per the standing exclusion above, don't assume it's wanted
just because a full migration was requested).

**Scraping**: the attachments scraper is already in the customer's
working directory (same convention as Phase 0's main scraper) — it has
its own README; read and follow it rather than guessing invocation. It
produces one or more zip files of job photos/documents (confirmed
example: three ~25 GB parts totaling ~54 GB), where the folder structure
inside each zip is `{job_number}/{filename}` — no per-file cleaning or
schema transform step exists for this entity, unlike every other entity
in this pipeline.

**Uploading — via Lighthouse's dedicated Job Attachment Uploader**, not
the local `upload-tool.js` companion script some scraper packages also
ship (that script talks directly to Tempest's API via a local Node proxy
and needs a manually-pasted JWT — it's a fallback/dev tool, not the
normal path). The real tool lives at
`https://lighthouse.podium.com/data-migration/job-attachments?organizationUid=<org-uid>`
and needs no separate auth — it's already an authenticated Lighthouse
session.

Page anatomy:
- A **Tempest Organization UID** field, pre-filled for the customer.
- Three tabs: **Folder Upload**, **Manual Lookup**, **Errors**.
- A stats row: Records, Files, Ready, Skipped, Uploaded, Not Found, Failed.
- **Upload Ready** / **Reset** buttons.

**Folder Upload tab**: drag a folder or click **Choose Folder**. Expects
`CustomerName/{job_number}/files` on disk — the zips need to be
**unzipped first** (a folder picker can't reach into a zip). It matches
each `{job_number}` subfolder to a Tempest job automatically and marks
non-matches **Not Found**. ⚠️ **The actual folder selection has to happen
on the user's side** — `Choose Folder` opens a native OS picker that
`computer`/browser-automation tools can't see or drive, and with tens of
GB across thousands of files this is also far past `file_upload`'s
10 MB-per-call ceiling. Unzipping the parts into the right structure is
something this skill *can* do; clicking Choose Folder is not.

**Between multiple parts/batches (e.g. part1, part2, part3 of a large
attachment set), click Reset before the next Choose Folder.** The tool
does not automatically clear the previous batch's state — leaving the
prior part's finished stats/table on screen when a new folder gets
selected. Reset is a plain button click, so this step *is* something
this skill can do on its own between parts (unlike Choose Folder
itself).

**After a folder is selected there are two distinct phases** — don't
assume upload has started just because Records/Files populated:
1. **Lookup/matching** — the tool works through each `{job_number}`
   folder looking up its Tempest job; Ready/Not Found/Failed climb
   toward the Records total while a spinner shows next to Upload
   Ready/Reset, and the **Upload Ready** button stays disabled.
2. **Upload** — once matching finishes (Ready + Not Found + Failed +
   Skipped = Records, spinner gone), the button enables. Some sessions
   auto-start the upload at this point; if not, it needs a click.

**Standing instruction from the user: always self-monitor this page's
progress rather than waiting to be told it's done.** After a folder is
selected (by the user — see the constraint above), take it from there
autonomously: check back periodically (screenshot the stats row) until
lookups finish, upload begins, and then completes (Ready hits 0), the
same way this skill's `/loop`-based polling pattern works for a running
upload. Only hand back to the user once a part is fully uploaded and
triaged, or if something needs their input (e.g. Reset, or the next
Choose Folder).

**Manual Lookup tab**: for adding/retrying specific job numbers by hand
— a `Job number` input, **Choose Files**, and **Add to Queue**. Populates
the same kind of table as Folder Upload (Job Number, Files, matched
Tempest Job UID + `import_job_id`, Existing/Uploaded counts, Status,
Error) — use this to patch in the stragglers a folder run couldn't match,
or for one-off manual attachment adds outside a bulk run.

**Errors tab**: a table of `job_number`, `paths` (every file that was
staged for that job), and `error` (e.g. `"No matching job found"`), plus
**Failed Files ZIP** and **Not Found CSV** download buttons for offline
triage.

**Triage rule for "No matching job found" (confirmed with the user)**,
before treating a job as a genuine gap:
1. **Check it isn't just a mismapping first** — confirm the job number in
   the folder name genuinely doesn't exist in Tempest under that exact
   number (formatting differences, leading zeros, etc. can cause a
   spurious non-match).
2. **If it truly doesn't match, check whether that job is in
   `cleaned-data/jobs-non-importable.csv`.** If it is, that's expected
   and not a bug — the job was never successfully imported as a Job
   History record in this migration, so there's naturally no Tempest job
   to attach files to. This is the exact same "job not found" pattern
   this skill's Phase 3 "Triaging failures" section documents for
   Invoices/Estimates above — treat it the same way (non-importable, no
   further action) rather than re-investigating from scratch.
3. If the job_number is in neither Tempest nor
   `jobs-non-importable.csv`/`jobs.csv`, that's a genuine gap worth
   flagging to the user rather than silently filing away.

**Handling "Failed" rows (matched job, upload itself failed) — confirmed
with the user:** the Errors tab's `Failed Files` section is distinct from
`Not Found` — these are files whose job *did* match a Tempest job but the
individual file upload errored (e.g. a transient "Failed to upload X",
or a hard `"Upload too large (max 16 MB)"` limit). Cross-check each
failed job_number against `jobs.csv` the same way as the Not Found
triage — if it's in `jobs.csv`, the match is real and the file is worth
retrying (unless the error is a hard limit like the size cap, which a
retry can't fix — flag those to the user instead of re-attempting).

**Don't retry these one-by-one via Manual Lookup as you find them** — a
job number that already appears in the current Folder Upload batch (even
if only some of its files failed) shows **"This job is already queued"**
and refuses a fresh Manual Lookup add for that same job number. Instead,
**batch all genuinely-retriable failures together and re-upload once,
after every part/batch for this customer has finished**:
1. Work through all parts (part1, part2, part3, ...) via Folder Upload
   first, letting each one fully complete.
2. After the *last* part finishes, collect every `Failed` row across all
   parts' Errors tabs whose job_number is confirmed in `jobs.csv` (per
   the cross-check above) — excluding any hard-limit failures a retry
   can't fix.
3. Build a fresh folder (e.g. `job-attachments/reupload/{job_number}/`)
   containing just those specific failed files, mirroring the same
   `{job_number}/{filename}` structure Folder Upload expects — not the
   entire original job folder, just the files that actually failed, to
   avoid re-uploading duplicates of files that already succeeded.
4. Run one more Folder Upload pass pointed at that `reupload/` folder
   (still requires the user to click Choose Folder — see the constraint
   above), then re-check its Errors tab the same way.

## Phase 4 — Wrap-up: failure-reasons breakdown

**"Work list" here includes the non-CSV entities too, per the completeness
principle at the top of this file** — Users/Technicians created and
designated, and Membership Plans / Estimate Templates set up via Operator
or Mock, not just the CSV-wizard entities. Don't call a migration
wrapped-up while any of those are still `NOT STARTED` without the user
having explicitly signed off on deferring them.

Once every entity in the work list has been uploaded (or explicitly
skipped/deferred with the user's sign-off), produce a simple, easy-to-digest
**HTML breakdown of every reason imports failed across the whole
migration** and publish it as an Artifact. Pull the reasons from the
downloaded Lighthouse error-report CSVs (this skill's Phase 3 "Triaging
failures" step) and from any `-non-importable.csv` filing decisions made
along the way — group by entity, then by failure reason, with row counts
for each group (e.g. "Invoices — 919 rows: job not found (job never
existed in the scrape)"). This is a reporting step, not a data fix —
don't re-attempt any imports as part of producing it.

**🎯 Use `references/migration-exceptions-template.html` (in this skill's
folder) as the literal starting point — don't redesign this page from
scratch.** It's the real, finished HTML from a prior migration's
breakdown (MLD Services), confirmed by the user as exactly the layout,
interactions, and copy style to keep for every future breakdown
(2026-08-25: "I love how you can see percentages of what wasn't
imported, I love how the boxes at the top are clickable, I like the
words that are stated, I like everything ... always make the html
breakdown exactly like this one just with the customer specific data").
Copy the file, then swap in this customer's data — masthead account name
and stats, tile counts, per-entity rows/reasons/tables — leaving the CSS,
layout structure, interaction JS (tile click → scroll-to-section), and
copy/microcopy patterns untouched. Do **not** invoke the `artifact-design`
skill for this page — the design question is already answered by the
template; only load `artifact-design` if the user explicitly asks for a
different look for a given migration.

What the template contains, for reference when adapting the data into it:
- **Masthead**: account name + a small stats strip (categories scanned,
  total rows scanned, total excluded, generated date).
- **Summary tiles**, one per entity/category, in a grid: excluded count
  (large, tabular-nums), "of N scanned", a thin percentage bar, and a
  border-top accent color that's green when that category is fully clean
  (0 excluded) vs. the accent color when it has exclusions. Clicking a
  tile scrolls to that entity's section (see the `addEventListener`
  wiring near the bottom of the template's `<script>`).
- **Per-entity section**: a title, an "N excluded of M scanned" pill,
  then — if clean — a single green "nothing held back" line and nothing
  else (don't render an empty table); if not clean — a horizontal
  **stacked reason bar** (segment width = share of that reason) with a
  matching legend showing each reason's label and count, then a full
  **scrollable table** (sticky header, monospace/tabular-nums for
  IDs/dates/money) of every excluded row with a trailing "Why excluded"
  column rendering one small chip per reason.
- **Reason labels must be computed from the actual data** (which
  required field is blank, which foreign key doesn't resolve, which
  amount is $0), not guessed — and when a row doesn't fit any known
  blank-field rule, label it honestly as needing manual review rather
  than inventing a plausible-sounding cause (verified this against the
  source CSVs before trusting a reason — see the invoice/customer
  cross-check pattern from this same session: a job_id that looks
  missing might actually resolve fine, so check before asserting "not
  linked to a job").
- Visual treatment: industrial/utilitarian "manifest" feel (condensed
  display face for headings, monospace for data/figures, restrained
  accent color) rather than a soft dashboard look — fits the
  inspection-report nature of the content. This is baked into the
  template's CSS already; don't reinterpret it per customer.

## Folder conventions (customer working directory)

```
<Customer>/<date> upload/
  <Scraper Package>/                the exporter tool, unzipped, with its own README.md
  raw/                              pre-cleaning scraper output, one CSV (or workbook) per entity
    <Customer Name>_<entity>.csv
  cleaned-data/                     Phase 2 output — upload-ready data
    <entity>.csv                    e.g. jobs.csv, customers.csv, invoices.csv, estimates.csv,
                                     pricebook-materials.csv, pricebook-services.csv, members.csv
    <entity>-non-importable.csv     same columns as <entity>.csv, no header changes —
                                     append rows here as failures are proven non-importable
    new-since-8-6/<entity>.csv      delta-only rows from a rescrape (e.g. dated by last full scrape)
  reupload/                         scratch/staging area, ephemeral per retry cycle
    <entity>.csv                    rows being retried right now; delete/clear once resolved
                                     (either they succeed, or they move to -non-importable)
```

`~/Downloads/failures-<timestamp>/` holds archived error-report CSVs
downloaded from Lighthouse during triage (see Phase 3's "Triaging
failures" above). For a standalone re-upload/retry request without a
fresh scrape, only `cleaned-data/` (and `reupload/` once triage starts)
needs to exist — `raw/` and the scraper package are only required if
Phase 1/2 are also being run.

## Caution

This pipeline ends in a write to a **live, shared production system**
(Podium). Credentials for the source FSM are sensitive — never log,
print, or commit `.env` files or scraped credentials. Don't invent data to
fill a required field; when the source is genuinely missing something
required, that row belongs in `-non-importable.csv`, not a guess.

Before clicking "Upload to FSM" in Phase 3:
- Confirm Mapping-step field assignments against the real source file,
  not just the AI's stated confidence.
- Only proceed past Review if Errors-only is empty (or you've explicitly
  decided, with the user, that outstanding errors are acceptable for this
  pass) — Warnings-only rows are fine to leave as-is per this shop's
  process.
- Never invent a mapping, technician match, or non-importable
  classification the source data doesn't actually support — when a
  failure reason or row's fate is ambiguous, cross-reference the raw
  data and ask rather than guessing.
