---
name: customer-audit
description: Run a full account-history audit on a specific Podium customer and produce a published HTML artifact — a bottom-line summary, company profile, product/contract ledger, a transcript-level "what were they sold on" audit of their Gong sales calls, recurring complaints, a dated timeline, and watch items. Starts from the customer's Lighthouse URL, opens their case in Salesforce, walks the account's entire Activity Timeline, and reads the full Gong transcripts of the sales calls. Use whenever the user asks to "run an audit" / "audit this customer" / "do a customer history audit on X" / "what were they sold on" / "pull their whole Podium history", or hands over a Lighthouse location URL for that purpose.
---

# Customer Audit

Produces one deliverable: a **published Artifact** titled
`<Company> — Podium Account Audit`, built by copying
`templates/audit-template.html` and swapping in the customer's data. The
research feeding it comes entirely from **Claude in Chrome** browser
automation against Lighthouse, Salesforce, and Gong — there is no API.

This is a **read-only** workflow. You view records; you never click a
send / submit / save / status control in Salesforce or Gong. The only
thing you create is the private Artifact.

Load the core Chrome tools before starting if they aren't already loaded:

```
ToolSearch("select:mcp__claude-in-chrome__tabs_context_mcp,mcp__claude-in-chrome__navigate,mcp__claude-in-chrome__computer,mcp__claude-in-chrome__read_page,mcp__claude-in-chrome__find,mcp__claude-in-chrome__get_page_text,mcp__claude-in-chrome__javascript_tool")
```

## Input

The customer's **Lighthouse URL**
(`https://lighthouse.podium.com/locations/<org-uuid>/<case-id>`). If the
user hasn't given it, **ask for it** — it is customer-specific and not
guessable.

---

## Phase A — Get into Salesforce

1. `tabs_context_mcp{createIfEmpty:true}`, then `navigate` the tab to the
   Lighthouse URL.
2. Wait ~3s for the skeleton loaders to resolve, then `screenshot`. You
   should see the case panel with the company name and address.
3. **Top-right of the case panel**, next to the local time, is a
   **hamburger (≡) icon**. Click it. A dropdown opens with items like
   "FSM Parent/Child", "Open Location in Admin", "Open Case in
   Salesforce", "Copy Case Id", "Close Case".
4. Click **"Open Case in Salesforce"**. It opens a new tab.
5. **Okta gate:** if that new tab lands on `podium.okta.com` ("Podium —
   Sign In"), **stop and tell the user to sign in via Okta**, then wait.
   You cannot screenshot or act on the okta.com domain. Often Salesforce
   is already authenticated and no prompt appears.
6. When it resolves you're on the Case:
   `podium.lightning.force.com/lightning/r/Case/<case-id>/view`. Note the
   case number and the "Warner"-style case title (e.g. "… – Expansion
   Onboarding"), status, owner, CSM, AE — these feed the summary.

## Phase B — Reach the account's Activity Timeline

1. On the Case, the **left column has an "Account" box** (under
   "Onboarding Team"). It has an **"Org Account Details" hyperlink** as
   its header. Find it with
   `find("Org Account Details hyperlink in Account box")` and click the
   returned ref. This navigates the same tab to the **Account** record
   (`/lightning/r/Account/<acct-id>/view`).
2. The Account page's **right rail is the Activity panel**. Scroll it
   into view; at the bottom of its filter bar is a **"View All"** link
   (next to "Refresh · Collapse All"). Click it.
3. A new tab opens:
   `podium.lightning.force.com/runtime_sales_activities/activityViewAll.app?parentRecordId=<acct-id>`
   **Record this exact URL** — it is the "return here for detail" source
   link in the Artifact.

## Phase C — Ingest the entire Activity Timeline

The page renders **every** activity into the DOM as a `<table>` element
(one per activity, newest first), but `get_page_text` output is capped at
~50 KB, so a single call only returns the most recent slice.

Extraction loop:

1. `get_page_text` on the tab → it saves a persisted file → **read that
   file fully**.
2. Note the date of the last *fully-captured* entry.
3. Via `javascript_tool`, remove already-captured activity tables from
   the top of the DOM:
   ```js
   const t = document.querySelectorAll('table');
   const n = t.length;
   for (let i = 0; i < N && i < n; i++) t[i].remove();
   'removed ' + N + ' of ' + n
   ```
   Choose **N a bit smaller** than the number of entries you just
   captured, so the next slice overlaps the previous one.
4. `get_page_text` again → read → confirm the new slice's first entry
   date is **≤** the previous slice's last captured date (overlap = no
   gap). If there's a gap, you removed too many — reload the page
   (`navigate` to the same URL) and restart with a smaller N.
5. Repeat until the slice reaches the **oldest** activity (typically a
   "Meeting Booked" / Calendly / account-setup entry from the signup
   year, with nothing older).

**Do not** try to pull the text via `javascript_tool` returning
`innerText` / `btoa` / base64 — the Chrome tool blocks cookie,
query-string, and base64-looking payloads. `get_page_text`'s
persisted-file output is the only reliable path; the table-removal trick
is how you page through it.

For each activity capture: **subject, date, Assigned To, Related To, and
the full Comments body.** The Comments body holds the Gong call brief
(bullets + "Next steps"), the full email text, or the meeting details —
this is the raw material for the timeline and complaints. Collect every
`https://podium.app.gong.io/call?id=<n>` link together with that
activity's subject and date.

The "Due Date" field usually reflects the event date; fall back to "Last
Modified Date" when Due Date is blank.

## Phase D — Read the Gong sales-call transcripts

**Which calls:** pull the **full transcript** only for calls where Podium
**pitched a new product, quoted a price, or closed** — account reviews
that turn into a pitch, FSM/CRM demos, expansion/renewal calls, the
closing call. **Skip** pure onboarding-config calls, SDR
"left voicemail" / short scheduling calls, and internal check-ins — their
Gong brief from Phase C is enough. If the set isn't obvious, list the
candidates and confirm with the user.

For each selected call:

1. `navigate` the timeline tab (you're done paging it) to
   `https://podium.app.gong.io/call?id=<n>`.
2. **Okta gate:** the first Gong navigation almost always redirects to
   `podium.okta.com`. **Stop, ask the user to sign into Gong via Okta,
   wait**, then re-navigate to the call URL.
3. On the call page: at the **left edge of the media panel** is a small
   **">" chevron** (around x=95, y=145 at a 1141-px-wide viewport).
   Click it → a tab bar appears: Briefs / Outline / **Transcript** /
   Call Info / Points of interest / Slides.
4. Click **"Transcript"** (around x=310, y=145).
5. `get_page_text` on the tab → returns the full transcript as
   `Speaker \n m:ss \n text` blocks.
6. **The panel state does NOT persist across navigations** — redo steps
   3–4 for every call.
7. **Long calls (>~45 min)** truncate. The transcript rows are
   `.monologue-wrapper` elements:
   ```js
   const w = document.querySelectorAll('.monologue-wrapper');
   for (let i = 0; i < HALF && i < w.length; i++) w[i].remove();
   'removed ' + HALF + ' of ' + w.length
   ```
   Remove roughly the first half, `get_page_text` again for the back
   half, read both persisted files. Overlap by a few rows.

From each transcript, extract: **the specific claims, quotes, product
names, prices, discounts, contract terms, and ROI/anecdote framing** the
rep used, plus the customer's stated goals, objections, and any veto.

---

## Phase E — Build the Artifact

**Start from `templates/audit-template.html`.** Copy it whole. It is a
fully worked example built for "Warner Super Service."

Two things are true at once here:

- **The design is fixed.** Same look every time.
- **The content is not.** What gets emphasised, flagged, expanded, or
  kept to a line depends entirely on what matters for *this* account.
  The Warner fill is what a heavy, complicated account looks like — a
  clean account's audit is much shorter, and that's correct.

### Fixed — never change

- The **entire `<style>` block, byte-for-byte.**
- Every structural element, `class` name, and section `id`.
- The `<h2>` section headings, the `NN — …` eyebrow labels, and the
  `<nav class="toc">` list.
- `favicon` `🛰️`. Title = `<Company> — Podium Account Audit`.
  `description` = one sentence.

### Judgment — weight the content to the account

- **Lead with what matters for this account.** Whatever the single most
  important thing about the account is — a forced migration, an
  at-risk renewal, a spend jump against a shaky payment history, a
  broken integration, an owner who vetoed an expansion, a happy
  reference customer with nothing wrong — that is what the
  `#bottom-line` opens on and what `#watch` is built around. Don't bury
  it to keep section lengths even.
- **Flag account-specific issues wherever they land hardest.** If
  something important doesn't fit an obvious section, give it a home
  anyway: its own `.lrow` in the ledger, its own `.cx` in complaints,
  its own `<ol>` item in watch items, a `<strong>` sentence in the
  bottom line. Better repeated across two sections than absent.
- **Don't pad a thin section.** A section that has little real content
  for this account should be short — a few lines, one card, or a single
  honest sentence ("No recurring billing friction on record."; "One
  sales call on file — the original 2023 signup."). Do not invent
  friction, risks, or pricing drama to match the template's volume.
- **A section with nothing real can collapse to one line**, but keep the
  section, its `<h2>`, and its TOC entry. Only the `#sold` cards and the
  `tl pin` rows scale to zero cleanly — if there are genuinely no
  audited sales calls, say so in one `<p>` where the `.audit` block was.
- **Severity and `pin`/`kind` tags must reflect reality**, not habit —
  a low-friction account's complaints are `sev-low`, its timeline may
  have no `k-friction` rows at all.

### Section reference (fill each with what the account actually has)

| Section (`id`) | Fill with |
|---|---|
| `<title>` + masthead | `eyebrow` = "Podium · Account Audit · prepared &lt;today&gt;". `h1` = company name. `.sub` = one-line framing of the account's current situation. `.meta` chips = 5–6 short facts (trade, city, DBA, "Customer since …", `SF Case …`, package). |
| `#bottom-line` (`.panel.bottomline.prose`) | Short `<p>`s (as few as 3, as many as 6). Who they are; when they became a customer + original footprint; current product stack + blended monthly spend; account health; **and, first or last, the one thing that most matters about this account right now.** `<strong>` the load-bearing facts. |
| `#profile` (`.profile` of `.pgroup` cards) | Cards: **The business**, **People**, **Systems &amp; operations**, **Podium relationship** (`.span2`), **Record IDs** (`.ids.stack`). Drop any `dt/dd` row — or a whole card — you have no real data for. **Never** use the stale SF "Employees" / "Total Locations" numbers. |
| `#ledger` (`.ledger` of `.lrow`) | One `.lrow` per product purchase / pricing event / contract term, chronological. `.when`, `.what` (product + `<small>` detail), `.cost` (add class `free` for waived periods). Add a "Projected total spend" row when a migration/expansion moves the number. A simple account may be 2–3 rows. |
| `#sold` (`.audit` of `<article class="call">`) | One card per **audited** sales call — as many as there are, possibly one, possibly none. Header: `.date` ("3 Jun 2026 · 1h 14m"), `h3`, `.rep` ("Jon Meyers → Danielle"). Body: optional framing `<p>`; `<p class="pitch-label">Pitched</p>`; `<ul class="sold">` of the specific transcript claims/quotes/prices; `<div class="reality">` with `<span class="tag">Since then</span>` (or "Now") + a `<p>` on how it played out. Add class `settled` to `.reality` if resolved. If there are none, replace the `.audit` block with one `<p>` saying so. |
| `#complaints` (`.complaints` of `.cx`) | One `.cx` per recurring friction theme, class `sev-high` / `sev-med` / `sev-low` per real severity. `h4` = theme + `<span class="sev">` timeframe/status. `<p>` describes it. Optional `<p class="win">` for a resolution/consequence with `<b>` on the payoff. A clean account may have one `.cx` or a single "no significant recurring friction" line. |
| `#timeline` (`.timeline` of `.tl`) | Every meaningful activity, **oldest → newest**. Intro `<p>` names the date span; mention the amber dots only if there are `tl pin` rows. Each `.tl`: `.date`, `.body h4` (title + `<span class="kind k-…">`), `.body p` (1–2 sentences; Gong transcript `<a>` for audited calls). Kind classes: `k-sale`, `k-onboard`, `k-friction`, `k-billing`, `k-milestone`, or bare `.kind` (Check-in / Admin / Advocacy). `class="tl pin"` on audited sales calls only; their count matches `#sold`. |
| `#watch` (`.watch`) | `h3` + `<ol>` of the real risks/actions going into whatever's next for this account — as few as 2, as many as ~5. `<strong>`-lead each. If the account is genuinely low-risk, say that plainly in 1–2 items rather than manufacturing concerns. |
| `#sources` | `.srclist` rows: **always** the SF Activity History URL (label "return here for detail"), the SF Account URL, the SF Case URL, then one row per audited Gong call. Then `<p class="disclaimer">`: compiled date, what it's based on, and a note that stale SF fields (headcount / locations) were disregarded. |

Then publish with the `Artifact` tool (`file_path` to your copy,
`favicon` `🛰️`, the title and one-sentence description).

Leave the browser tabs open. Hand the user the Artifact URL plus a short
prose recap of the findings.

## Notes / gotchas

- **Two separate Okta gates.** Salesforce is often already authed; Gong
  almost always prompts. Handle each as it appears — you can't automate
  past okta.com.
- **Don't guess coordinates blindly.** The chevron/tab x-coords above
  assume a ~1141-px viewport; `zoom` into the top-left of the Gong panel
  to confirm before clicking if a click misses.
- **Overlap every text slice.** For both the activity timeline and long
  transcripts, always verify the next slice starts at or before the end
  of the previous one before removing more DOM.
- If the customer has more or fewer audited calls than the template's
  four, **add or delete** `<article class="call">` blocks and
  `class="tl pin"` timeline rows so the two sections agree.
