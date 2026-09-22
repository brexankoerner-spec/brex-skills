#!/usr/bin/env python3
"""
Podium Migration Standard — Phase 2 cleaning template.

PROVENANCE: this is not a from-scratch design — it's the reusable core
extracted from two real, working migration scripts, with the bugs those
scripts didn't yet know about fixed in:
  - Apex Residential (HouseCall Pro, single .xlsx workbook source)
    -> Documents/Customer Data/Apex Residential/upload-8-17/clean.py
  - MLD Services (Jobber, per-entity CSV sources)
    -> Documents/Customer Data/MLB Services/upload 8-13/clean.js (was JS, ported here)

HOW TO USE: copy this file into the customer's working directory as
`clean.py`, fill in the `# CUSTOMIZE:` marked spots (raw file location/shape,
column names for this specific FSM export, and any FSM-specific quirks), and
delete what you don't need (e.g. no Equipment entity this migration). The
generic helpers below (formatting, contact dedup/merge, required-field
splitting, money conversion, exact CSV headers, delta detection) are already
correct per SKILL.md's Phase 2 rules — don't rewrite them, only the
FSM-specific column mapping and per-entity wiring in the pipeline section at
the bottom should change per customer.

Fixes baked in here that neither original script had (both were confirmed as
real bugs only after their outputs were uploaded — see SKILL.md's Phase 3
"Triaging failures" for the full stories):
  1. `convert_line_items_money` — line_items_json unit_price/unit_cost as
     dollar strings caused a 100%-failure upload (4,236/4,236 rows) on one
     Invoices import. Neither clean.py nor clean.js converted these.
  2. `pick_primary_phone_email` — blindly zipping phones[0]/emails[0] as a
     contact's primary pair corrupted a household-of-2 record (the "Meagan
     Rose / Ethan Glenn" case) because the source's phone/email arrays
     aren't guaranteed to be index-aligned per person. Both original scripts
     did the naive zip.
  3. `fix_shared_identifier_conflicts` — generalized from Apex's clean.py
     (which only ran it in the email direction) to also run in the phone
     direction; MLD's clean.js didn't have this step at all.

Read SKILL.md's Phase 2 in full before running a migration — this script
encodes the *mechanics* of the rules, not the judgment calls. In
particular, SKILL.md's Phase 2 has a "judgment-call gate": some of the
functions below implement a heuristic fix that's a genuine guess, not a
deterministic right answer, and must NOT be called automatically as part
of the pipeline — the pattern has to be detected in the real data first,
explained to the user with concrete examples, and explicitly confirmed
before applying. `fix_shared_identifier_conflicts` and
`build_job_start_end_multiday_variant` are gated this way (see their own
docstrings for exactly what to do); so is anything else you notice that
doesn't cleanly fit a documented rule — check SKILL.md's "Known FSM data
quirks catalog" before deciding how to handle it, and flag genuinely
novel patterns to the user rather than picking a default yourself.
"""

import csv
import json
import re
from collections import defaultdict
from datetime import datetime, timedelta

# ============================================================================
# CUSTOMIZE — per-migration constants
# ============================================================================
CUSTOMER_NAME = 'CUSTOMER NAME'  # CUSTOMIZE
OUT = 'cleaned-data'

# --- Pick ONE raw-source reader, delete the other block. ---

# Option A: single .xlsx workbook (e.g. HouseCall Pro's merge-script output).
# import openpyxl
# RAW_XLSX = f'raw/{CUSTOMER_NAME} - HouseCall Pro.xlsx'  # CUSTOMIZE
# wb = openpyxl.load_workbook(RAW_XLSX, read_only=True, data_only=True)
# def sheet_rows(sheet_name):
#     ws = wb[sheet_name]
#     headers = [c.value for c in next(ws.iter_rows(min_row=1, max_row=1))]
#     for r in ws.iter_rows(min_row=2, values_only=True):
#         yield dict(zip(headers, r))

# Option B: one CSV per entity (e.g. Jobber exporter output).
RAW_DIR = 'raw'
def read_csv(entity_filename):
    """entity_filename e.g. 'contacts', 'jobs', 'invoices' -> raw/<Customer>_<entity>.csv"""
    path = f'{RAW_DIR}/{CUSTOMER_NAME}_{entity_filename}.csv'
    with open(path, newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


# ============================================================================
# 1. GLOBAL FORMATTING HELPERS (SKILL.md Phase 2, rule 2)
# ============================================================================

_SPREADSHEET_ESCAPE_RE = re.compile(r'^="(.*)"$')

def clean(v):
    """
    Strip whitespace + un-escape Excel/Sheets-style ="123" values.
    Confirmed necessary for CSV exports (MLD/Jobber raw CSVs had these);
    NOT needed when reading straight from an .xlsx via openpyxl (Apex's
    HouseCall Pro workbook didn't have them — openpyxl already gives the
    real value). Safe to call on both either way.
    """
    if v is None:
        return ''
    s = str(v).strip()
    m = _SPREADSHEET_ESCAPE_RE.match(s)
    return m.group(1) if m else s


def norm_phone(v):
    """10-digit US phone, digits only, '' if unparseable. Strips a leading
    country-code '1' from an 11-digit number."""
    if not v:
        return ''
    digits = re.sub(r'\D', '', str(v))
    if len(digits) == 11 and digits.startswith('1'):
        digits = digits[1:]
    return digits if len(digits) == 10 else ''


def fmt_phone(digits):
    """Optional (xxx) xxx-xxxx display formatting — MLD's convention.
    Apex instead left phones as bare digits; both imported fine in
    Lighthouse. Pick one per customer and stay consistent within that
    customer's cleaned-data files."""
    return f"({digits[0:3]}) {digits[3:6]}-{digits[6:10]}" if len(digits) == 10 else digits


def norm_email(v):
    s = clean(v).lower()
    return s if re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', s) else ''


def split_multi(v):
    """Splits a semicolon-separated multi-value raw field (Jobber commonly
    combines multiple phones/emails/job-ids into one ';'-joined column)."""
    return [p.strip() for p in clean(v).split(';') if p.strip()]


# ============================================================================
# 2. JUNK / SHARED PHONE DETECTION (SKILL.md Phase 2, rule 3 — blacklist)
# ============================================================================

STATIC_JUNK_PHONES = set()
# CUSTOMIZE: after inspecting the raw data, add confirmed office-line/dummy
# numbers here. Apex Residential's blacklist (for reference) included the
# company's own office line plus several obvious test numbers like
# '7777777777' and a toll-free '8005559981' — these aren't detectable by
# pattern alone and had to be found by actually looking at who a number was
# attached to across many unrelated contacts.


def is_junk_phone_pattern(digits):
    """Static pattern-based junk detection — catches obvious dummy/test
    numbers without needing any customer-specific inspection."""
    if not digits or len(digits) != 10:
        return True
    if len(set(digits)) == 1:  # 1111111111 etc.
        return True
    if digits in ('1234567890', '0123456789'):
        return True
    if digits.startswith('800555') or digits.startswith('555555'):
        return True
    return False


def find_dynamic_junk_phones(records, get_phones, get_owner_key, min_distinct_owners=4):
    """
    A phone shared across `min_distinct_owners`+ genuinely distinct people
    (different name+address combos) is a shared/office line, not a real
    personal number — auto-detected instead of hand-curated. Confirmed
    technique from MLD Services' clean.js. `get_owner_key(record)` should
    return something like f"{full_name}|{street_address}".
    """
    owners_by_phone = defaultdict(set)
    for r in records:
        owner = get_owner_key(r)
        for p in get_phones(r):
            owners_by_phone[p].add(owner)
    return {p for p, owners in owners_by_phone.items() if len(owners) >= min_distinct_owners}


# ============================================================================
# 3. CONTACT DEDUP / MERGE FRAMEWORK (SKILL.md Phase 2, rule 3)
# ============================================================================

class UnionFind:
    def __init__(self):
        self.parent = {}

    def find(self, x):
        self.parent.setdefault(x, x)
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[rb] = ra


PM_TITLE_RE = re.compile(r'propert.*manag|landlord|realtor|real\s*estate\s*agent', re.I)


def group_should_block_merge(group_phones, group_emails, group_addresses, group_job_titles,
                              max_identifiers=2, max_address_union=5):
    """
    Anti-over-merging rule for property-management/commercial accounts.
    group_phones / group_emails: sets of distinct normalized values across
    the WHOLE candidate merge group (not per-record). group_addresses: the
    UNION of normalized street addresses across the group — a property
    manager can show up as many separate low-address-count source records
    that only look large in aggregate (confirmed case: one email reached 28
    candidate rows / 25 distinct addresses this way, no single record
    tripped a per-record threshold). group_job_titles: iterable of raw
    job_title strings from every record in the group.
    """
    if len(group_phones) > max_identifiers or len(group_emails) > max_identifiers:
        return True
    if len(group_addresses) >= max_address_union:
        return True
    if any(t and PM_TITLE_RE.search(t) for t in group_job_titles):
        return True
    return False


def pick_primary_phone_email(phones, emails, singular_phone=None, singular_email=None):
    """
    ⚠️ SAFETY FIX for a confirmed bug (MLD Services / Jobber). Naively
    zipping phones[0] with emails[0] as "the" primary pair is wrong when one
    source contact record represents a household of 2+ real people and the
    phones/emails arrays aren't guaranteed to be index-aligned per person —
    confirmed case: a "Meagan Rose" record had phones=[Meagan's, Ethan's]
    but emails=[Ethan's, Meagan's] (reversed), and naive zipping cross-wired
    Meagan's phone to Ethan's email. This only surfaced later at Lighthouse
    upload as an "identifier conflict: phone and email resolve to different
    Rolodex contacts" error. Neither the Apex nor the original MLD script
    had this guard.
    `singular_phone`/`singular_email`: pass the source's own singular
    client.phone/client.email fields if it exposes them separately from the
    plural arrays — those are the safest correlated pair when available.
    """
    phones = [p for p in phones if p]
    emails = [e for e in emails if e]
    if len(phones) >= 2 and len(emails) >= 2:
        if singular_phone or singular_email:
            primary_phone = singular_phone or phones[0]
            primary_email = singular_email or emails[0]
        else:
            # No reliable per-person correlation available — keep only the
            # one most load-bearing identifier as primary rather than
            # asserting a pairing the data doesn't support.
            primary_phone = phones[0]
            primary_email = ''
        extra_phones = [p for p in phones if p != primary_phone]
        extra_emails = [e for e in emails if e != primary_email]
        return primary_phone, primary_email, extra_phones, extra_emails
    primary_phone = phones[0] if phones else ''
    primary_email = emails[0] if emails else ''
    return primary_phone, primary_email, phones[1:], emails[1:]


def fix_shared_identifier_conflicts(rows, notes_field='contact_notes'):
    """
    After a PM-block split leaves the same email (or phone) on multiple rows
    with genuinely different counterpart phones (or emails), Podium's
    Rolodex can't resolve identity and every one of those rows fails at
    upload with "identifier conflict: phone and email resolve to different
    Rolodex contacts". Keep the identifier on one canonical row per
    conflicting group (the one with the most complete notes), blank it on
    the rest. Ported from Apex's clean.py (which only ran this in the email
    direction) and generalized to run in the phone direction too — MLD's
    clean.js didn't have this step at all, and its outputs did hit this
    failure class at upload time.

    ⚠️ DO NOT CALL THIS AUTOMATICALLY AS PART OF THE PIPELINE. Picking a
    "canonical" row by most-complete-notes is a guess about which record is
    the "real" one — SKILL.md's Phase 2 judgment-call gate requires
    detecting every blocked group first, explaining the mechanism and
    showing concrete examples to the user, and getting one batch
    confirmation covering the whole migration before calling this. If the
    user declines, do not fall back to some other default here either — go
    back and ask them how they want the conflicts handled instead. See
    SKILL.md's rule 3 ("Blocking the merge is not enough on its own") for
    the full script.

    Mutates and returns `rows` (list of dicts with 'phone'/'email' keys).
    """
    for field, counterpart in (('email', 'phone'), ('phone', 'email')):
        groups = defaultdict(list)
        for r in rows:
            v = (r.get(field) or '').strip()
            if v:
                groups[v.lower() if field == 'email' else v].append(r)
        for group in groups.values():
            counterparts = {(r.get(counterpart) or '').strip() for r in group}
            if len(counterparts) > 1:
                canonical = max(group, key=lambda r: len(r.get(notes_field, '') or ''))
                for r in group:
                    if r is not canonical:
                        r[field] = ''
    return rows


def recover_link_by_name(name, name_count, name_to_master):
    """
    If a Job/Invoice/Estimate row has no phone/email/job_id link, fall back
    to matching its customer_name against the cleaned Customers set — ONLY
    if that name is unique there. Ambiguous name -> no recovery (row stays
    non-importable). Confirmed pattern from both Apex and MLD scripts.
    ⚠️ Per SKILL.md: "unique in Customers" is necessary but NOT always
    sufficient — company contacts (business name only in company_name, both
    first/last blank) can pass this check and still fail 100% at Lighthouse
    upload because customers.csv has no company_name column to match
    against. This function recovers what's mechanically recoverable; it
    does not replace the "ask the user about company-contact promotion"
    judgment call SKILL.md documents.
    `name_to_master[key]` values must have 'phone'/'email' keys.
    """
    key = (name or '').strip().lower()
    if not key or name_count.get(key, 0) != 1:
        return '', ''
    master = name_to_master[key]
    return master.get('phone', ''), master.get('email', '')


# ============================================================================
# 4. JOB DATE HELPERS (SKILL.md Phase 2, JOBS schema notes)
# ============================================================================

def _parse_flexible(v):
    if not v:
        return None
    try:
        return datetime.fromisoformat(str(v).replace('Z', '+00:00'))
    except ValueError:
        return None


def build_job_start_end(raw_start_date, raw_start_time, raw_end_date, raw_end_time,
                         work_status=None, created_at=None):
    """
    ✅ DEFAULT / RECOMMENDED strategy — "prefer the explicit start field"
    (per SKILL.md's 2026-08-14 superseded finding for Jobber). Use the
    source's own separate start date+time fields as-is; only fall back to
    end-minus-1h when start is genuinely missing. Do NOT override a real
    start just because start and end land on different dates — that
    "multi-day" heuristic was tried for Jobber and found to silently
    corrupt the majority of ONE_OFF jobs (~2,228 of 2,237), because the gap
    was usually just "completed a few days after it was scheduled," not a
    real multi-day span, and `endAt` on recurring jobs can carry far-future
    sentinel values besides. Use this for any FSM that exposes a real,
    separate start field.
    This is the safe, no-confirmation-needed default — call it unless the
    judgment-call gate on `build_job_start_end_multiday_variant` below has
    been explicitly satisfied for this migration.
    Returns (job_start_date_iso, job_end_date_iso).
    """
    if raw_start_date:
        start_iso = f"{raw_start_date}T{raw_start_time}:00" if raw_start_time else raw_start_date
        end_iso = f"{raw_end_date}T{raw_end_time}:00" if (raw_end_date and raw_end_time) else (raw_end_date or '')
        return start_iso, end_iso
    if raw_end_date:
        end_iso = f"{raw_end_date}T{raw_end_time}:00" if raw_end_time else raw_end_date
        dt = _parse_flexible(end_iso)
        start_iso = (dt - timedelta(hours=1)).isoformat() if dt else end_iso
        return start_iso, end_iso
    if work_status in ('complete rated', 'complete unrated') and created_at:
        return created_at, ''
    return '', ''


def build_job_start_end_multiday_variant(raw_start, raw_end, multiday_threshold_hours=24):
    """
    ⚠️ ALTERNATE strategy — "end-minus-offset for real multi-day spans"
    (Apex Residential/HouseCall Pro's clean.py; worked fine there, no
    superseding finding for HCP). Only reach for this on an FSM that does
    NOT expose a separate explicit start field, or after you've confirmed
    (per SKILL.md's cross-check-against-the-FSM's-own-report method) that a
    start/end gap really does mean a genuine multi-day job rather than
    scheduled-vs-completed drift. Do not use this as the default for a new
    FSM without that verification — it's exactly the heuristic that broke
    for Jobber.

    ⚠️ DO NOT CALL THIS AUTOMATICALLY. SKILL.md's Phase 2 judgment-call gate
    requires: (1) detecting whether the multi-day pattern (gap >
    `multiday_threshold_hours`) actually shows up in this account's data,
    (2) if the source is HouseCall Pro, telling the user this is a known,
    previously-confirmed quirk with counts/examples and offering this fix —
    apply only if they say yes; (3) if the source is any other FSM,
    consulting SKILL.md's "Known FSM data quirks catalog" first — cite the
    precedent if one exists, or flag it as a novel quirk and ask how to
    proceed if none does. Never call this as a default step in the
    pipeline, even for HouseCall Pro — "known quirk" means the explanation
    and fix are ready to offer, not that asking can be skipped.
    """
    sdt, edt = _parse_flexible(raw_start), _parse_flexible(raw_end)
    if sdt and edt and (edt - sdt) > timedelta(hours=multiday_threshold_hours):
        return (edt - timedelta(hours=1)).isoformat(), raw_end
    return raw_start, raw_end


# ============================================================================
# 5. MONEY HELPERS (SKILL.md Phase 2, INVOICES/ESTIMATES notes)
# ============================================================================

def dollar_to_cents(v):
    """
    For TOP-LEVEL required *_cents columns (total_cents, subtotal_cents,
    tax_amount_cents, ...). Blank/unparseable returns '' (empty), NOT 0, so
    the required-field check correctly routes the row to non-importable
    instead of silently accepting a fabricated $0. (Contrast with
    `convert_line_items_money` below, where blank genuinely means 0.)
    """
    s = clean(v).replace('$', '').replace(',', '')
    if s == '':
        return ''
    try:
        return str(round(float(s) * 100))
    except ValueError:
        return ''


def convert_line_items_money(line_items_json_str, money_fields=('unit_price', 'unit_cost')):
    """
    🚨 CONFIRMED CRITICAL FIX — neither the original Apex nor MLD cleaning
    script did this, and its absence caused a 100%-failure upload
    (4,236/4,236 rows) on one Invoices import before it was caught: the
    scraper emits nested line-item money as dollar strings ("$25.00"),
    which Lighthouse's import rejects outright with
    "line_items.N.unit_price: must be a integer". Preview (step 3 of the
    wizard) does NOT catch this — it looked clean (90% score, 0 errors) right
    up until the real upload failed. Always run this on every entity with a
    line_items_json column before writing cleaned-data.
    Blank/missing values convert to 0 cents (not left as a string) — an
    explicit zero is the honest reading of "no cost was ever recorded," and
    a naive None-only check misses the empty-string case (confirmed: 48
    rows failed silently this way on one account because unit_cost was ""
    rather than missing entirely).
    """
    if not line_items_json_str:
        return line_items_json_str
    try:
        items = json.loads(line_items_json_str)
    except (json.JSONDecodeError, TypeError):
        return line_items_json_str
    for item in items:
        for field in money_fields:
            if field in item:
                raw = str(item[field]).replace('$', '').replace(',', '').strip()
                try:
                    item[field] = round(float(raw) * 100) if raw else 0
                except ValueError:
                    item[field] = 0
    return json.dumps(items)


# ============================================================================
# 6. EXACT PODIUM MIGRATION STANDARD HEADERS (SKILL.md Phase 2, Schema definitions)
# ============================================================================
# These are copied verbatim from SKILL.md — don't retype them from memory,
# don't reorder them (the wizard's Mapping step matches by name, not
# position, but keeping order consistent avoids confusion when diffing).

HEADERS = {
    'customers': [
        'first_name', 'last_name', 'phone', 'email', 'street_address', 'unit',
        'city', 'state', 'postal_code', 'country', 'tags', 'contact_notes',
        'property_relation', 'property_type', 'quickbooks_customer_id',
    ],
    'jobs': [
        'job_id', 'customer_name', 'customer_phone', 'customer_email', 'job_title',
        'technician', 'job_start_date', 'job_end_date', 'job_type', 'status',
        'notes', 'address_street', 'address_unit', 'address_city', 'address_state',
        'address_postal_code',
    ],
    'invoices': [
        'external_id', 'status', 'job_id', 'customer_phone', 'customer_email',
        'total_cents', 'subtotal_cents', 'tax_amount_cents', 'discount_amount_cents',
        'issue_date', 'due_date', 'notes', 'line_items_json',
    ],
    'estimates': [
        'name', 'external_estimate_id', 'customer_name', 'customer_email',
        'customer_phone', 'job_id', 'total_cents', 'subtotal_cents',
        'discount_amount_cents', 'discount_percentage', 'valid_until',
        'created_at', 'notes', 'estimate_status', 'line_items_json',
    ],
    'pricebook-services': [
        'category', 'name', 'price', 'after_hours_price', 'description', 'taxable',
        'task_code', 'industry', 'unit_of_measure', 'unit_cost', 'materials',
        'duration', 'labor_rate', 'labor_duration', 'income_account', 'expense_account',
    ],
    'pricebook-materials': [
        'category', 'name', 'price', 'after_hours_price', 'description', 'taxable',
        'task_code', 'industry', 'unit_of_measure', 'unit_cost', 'material_number',
        'income_account', 'expense_account',
    ],
    'equipment': [
        'equipment type', 'name', 'manufacturer', 'model number', 'serial number',
        'install date', 'placement', 'status', 'manufacturer warranty end', 'notes',
        'customer number', 'location number', 'customer name', 'customer email',
        'customer phone', 'street address', 'unit', 'city', 'state', 'zip',
        'country', 'property type', 'job location',
    ],
    'members': [
        'contact name', 'phone number', 'email', 'service address', 'membership plan',
        'number of systems', 'start date', 'is auto renewal?', 'next auto renewal',
        'end date', 'last service date', 'next outreach date', 'notes', 'country',
        'status', 'notes.1',
    ],
}


def write_entity(entity, rows_ok, rows_bad):
    """Writes <entity>.csv and <entity>-non-importable.csv with the exact
    Podium Migration Standard headers, and prints the summary line SKILL.md's
    Phase 2 "Final reporting" step calls for."""
    headers = HEADERS[entity]
    with open(f'{OUT}/{entity}.csv', 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=headers, extrasaction='ignore')
        w.writeheader()
        w.writerows(rows_ok)
    with open(f'{OUT}/{entity}-non-importable.csv', 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=headers, extrasaction='ignore')
        w.writeheader()
        w.writerows(rows_bad)
    print(f"{entity}.csv: {len(rows_ok)} rows | {entity}-non-importable.csv: {len(rows_bad)} rows")


# ============================================================================
# 7. "NEW SINCE <date>" DELTA HELPERS (SKILL.md folder conventions)
# ============================================================================

def compute_new_since_by_id(rows_ok, id_field, previous_csv_paths):
    """
    ID-based delta (Apex Residential's clean_jobs.py pattern). Use when the
    previous export is known to be a complete, gap-free snapshot — simpler,
    but wrong if it had silent gaps (see the date-cutoff variant below).
    """
    prev_ids = set()
    for path in previous_csv_paths:
        with open(path, newline='') as f:
            for row in csv.DictReader(f):
                if row.get(id_field):
                    prev_ids.add(row[id_field])
    return [r for r in rows_ok if r.get(id_field) not in prev_ids]


def compute_cutoff_date(previous_csv_path, date_field):
    """
    Date-cutoff delta (MLD Services' clean.js pattern). Use when the
    previous export might have gaps — confirmed case: MLD's prior export
    was missing ~250 older invoices despite having newer ones, making
    ID/number presence unreliable as an "is this new" signal. The max date
    actually present in the old sheet is a safe cutoff regardless of
    earlier gaps.
    """
    dates = []
    with open(previous_csv_path, newline='') as f:
        for row in csv.DictReader(f):
            v = row.get(date_field)
            if v:
                dt = _parse_flexible(v)
                if dt:
                    dates.append(dt)
    return max(dates) if dates else None


def is_after_cutoff(iso_str, cutoff):
    if not cutoff or not iso_str:
        return False
    dt = _parse_flexible(iso_str)
    return bool(dt and dt > cutoff)


# ============================================================================
# 8. PIPELINE — CUSTOMIZE per entity, per FSM
# ============================================================================
# Below is a worked example wired to Apex Residential's real HouseCall Pro
# column names (its clean.py, proven across multiple real uploads) — copy
# the shape, swap the raw column names for this customer's actual export.
# Where MLD Services' Jobber columns differed meaningfully, that's noted
# inline for reference. ALWAYS do SKILL.md Phase 2 rule 1 first: inspect the
# actual raw headers yourself before trusting any column name below.
#
# Order matters and mirrors the upload order in Phase 3: Customers, then
# Jobs, then Invoices/Estimates (which link to Customers+Jobs), then
# everything else.

if __name__ == '__main__':
    import os
    os.makedirs(OUT, exist_ok=True)

    # ------------------------------------------------------------------ CUSTOMERS
    print("=== CUSTOMERS ===")
    # CUSTOMIZE: build one raw record per source contact, e.g.:
    #   raw_contacts = list(sheet_rows('Contacts'))          # xlsx source
    #   raw_contacts = read_csv('contacts')                  # per-entity CSV source
    #
    # For each raw record, normalize into a dict with at least:
    #   id, first, last, company, job_title, phones (list), emails (list),
    #   street, unit, city, state, postal, country, notes, created_at
    # (HouseCall Pro splits phone into mobile_number/home_number/work_number
    #  — priority Mobile > Home > Work, single value. Jobber instead gives a
    #  single ';'-joined `phone`/`email` column — use split_multi() on those.)
    #
    # Then:
    #   1. Blacklist junk phones BEFORE building merge keys:
    #        junk = STATIC_JUNK_PHONES \
    #             | {p for r in records for p in r['phones'] if is_junk_phone_pattern(p)} \
    #             | find_dynamic_junk_phones(records, lambda r: r['phones'],
    #                                        lambda r: f"{r['first']} {r['last']}|{r['street']}")
    #        for r in records: r['phones'] = [p for p in r['phones'] if p not in junk]
    #
    #   2. Union-find merge on phone / email / (name+street):
    #        uf = UnionFind()
    #        key_to_first = {}
    #        for r in records:
    #            for key in [('phone', p) for p in r['phones']] + [('email', e) for e in r['emails']] \
    #                      + ([('nameaddr', r['first'].lower(), r['last'].lower(), r['street'].lower())]
    #                         if r['first'] and r['last'] and r['street'] else []):
    #                if key in key_to_first: uf.union(key_to_first[key], r['id'])
    #                else: key_to_first[key] = r['id']
    #        groups = defaultdict(list)
    #        for r in records: groups[uf.find(r['id'])].append(r)
    #
    #   3. Per group: block via group_should_block_merge(...) (property-mgmt
    #      anti-over-merge) using the group's UNION of phones/emails/addresses
    #      and every member's job_title. If blocked, emit each member as its
    #      own row (still through pick_primary_phone_email per-member since a
    #      single blocked-out record can itself be a household case). If not
    #      blocked, merge into one master record — use
    #      pick_primary_phone_email(all_phones, all_emails, ...) for the
    #      master's primary phone/email, fold every other phone/email/note/
    #      extra-address into contact_notes, and remember the id->master
    #      mapping for FK relinking on Jobs/Invoices/Estimates/Equipment/Members.
    #
    #   4. Split importable: first_name required, AND (phone OR email) required.
    #   5. ⚠️ GATE: before calling fix_shared_identifier_conflicts, stop —
    #      per SKILL.md's Phase 2 judgment-call gate, tally every blocked
    #      group, show the user counts + concrete examples + how the
    #      canonical-row pick works, and get one batch confirmation for
    #      the whole migration. Only THEN call
    #      fix_shared_identifier_conflicts(all_output_rows) on the full
    #      customers.csv row set (not just the blocked ones — conflicts
    #      can arise from the merge step too). If declined, ask the user
    #      how they want it handled instead — don't pick a fallback here.
    #   6. write_entity('customers', cust_rows, cust_bad)
    #
    # Build `name_count` / `name_to_master` here too (Counter + dict keyed by
    # lowercased "first last") for the Jobs/Invoices/Estimates name-recovery
    # step below.
    raise NotImplementedError("CUSTOMIZE: wire up Customers per the notes above")

    # ------------------------------------------------------------------ JOBS
    print("\n=== JOBS ===")
    # CUSTOMIZE: for each raw job row, resolve customer_name/phone/email
    # either via the id->master relink from Customers (preferred, if the
    # source gives a customer/client id on the job) or via
    # recover_link_by_name(name, name_count, name_to_master) as a fallback
    # when there's no id and no direct phone/email on the job row.
    #
    # Dates: use build_job_start_end(...) by default — no confirmation
    # needed, this is always safe to call. ⚠️ GATE on
    # build_job_start_end_multiday_variant(...): don't call it just
    # because the source lacks a separate start field or "looks like"
    # HouseCall Pro. Per SKILL.md's Phase 2 judgment-call gate: detect
    # whether the multi-day pattern actually appears in this account's
    # data first, then — if HouseCall Pro, flag it as the known quirk and
    # offer the fix; if any other FSM, consult the "Known FSM data quirks
    # catalog" for a precedent (verify before porting) or flag it as
    # novel — and only call this after the user explicitly says yes.
    #
    # Required: job_id, customer_name, job_title, job_start_date all
    # non-blank, AND not ambiguous (see recover_link_by_name's docstring —
    # unique-name match is necessary but not sufficient; still route
    # company-contact-with-no-real-name cases to the user per SKILL.md
    # rather than silently importing or silently excluding).
    #
    # write_entity('jobs', job_rows, job_bad)

    # ------------------------------------------------------------------ INVOICES / ESTIMATES
    print("\n=== INVOICES ===")
    # CUSTOMIZE — 🚨 before wiring `external_id`, open the RAW csv yourself
    # and confirm which column is the real human-readable invoice number.
    # Confirmed bug (Jobber): raw `external_id` is the internal API id
    # (e.g. "MTY3OTMyODM3") — WRONG; raw `invoice_number` is the real short
    # number (e.g. "24567") — RIGHT. A same-shaped, identically-named
    # column is not proof it's correct. Same bug, same shape, in Estimates:
    # use `quote_number`, not `external_estimate_id`.
    #
    # total_cents/subtotal_cents/etc via dollar_to_cents(); line_items_json
    # via convert_line_items_money() — ALWAYS, every entity, every migration.
    #
    # Link recovery: phone/email from the Customers relink or
    # recover_link_by_name() fallback, same as Jobs. Required: external_id +
    # status + total_cents (Invoices) / name + total_cents + subtotal_cents
    # (Estimates), AND at least one of phone/email/job_id linked.
    #
    # write_entity('invoices', inv_rows, inv_bad)
    # write_entity('estimates', est_rows, est_bad)

    # ------------------------------------------------------------------ PRICEBOOK / EQUIPMENT / MEMBERS
    print("\n=== PRICEBOOK / EQUIPMENT / MEMBERS ===")
    # CUSTOMIZE per source. A few confirmed FSM-specific notes:
    #  - Jobber pricebook: a single `pricebook` export distinguishes
    #    materials via `category == 'PRODUCT'`; everything else is a Service.
    #  - Prices/unit_cost for Pricebook are in DOLLARS, not cents — divide by
    #    100 only if the source already has cents.
    #  - Members: if source is Jobber and `is_auto_renewal` is true, BLANK
    #    `end date`/`next auto renewal` outright rather than passing through
    #    — confirmed sentinel-date bug (same root cause as the Jobs
    #    multi-day issue): far-future placeholder values (365/731/1827/2191/
    #    3653-day spans) get emitted instead of "no known end date."
    #  - Equipment hard-requires a Contacts sheet in the same Lighthouse
    #    upload (see SKILL.md Phase 3) — that's an upload-time constraint,
    #    not a cleaning-time one, but keep it in mind when deciding whether
    #    to produce equipment.csv at all for a source with sparse/placeholder
    #    equipment data.
    #
    # write_entity('pricebook-services', svc_rows, svc_bad)
    # write_entity('pricebook-materials', mat_rows, mat_bad)
    # write_entity('equipment', equip_rows, equip_bad)
    # write_entity('members', mem_rows, mem_bad)

    # ------------------------------------------------------------------ NEW-SINCE-<date> DELTA (only for a rescrape/re-clean pass)
    # os.makedirs(f'{OUT}/new-since-<date>', exist_ok=True)
    # cutoff = compute_cutoff_date('../<prev upload>/cleaned-data/customers.csv', 'created_at')
    # new_customers = [r for r in cust_rows if is_after_cutoff(r.get('_created_at'), cutoff)]
    # ...write new_* files the same way as compute_new_since_by_id's callers do.

    print("\n=== DONE ===")
