---
name: account-configuration
description: Configure a customer's Podium account settings based on the configuration requests they made on a call — read a kickoff or data-review call transcript, extract every configuration ask, then implement each one by mocking into the customer's live Podium account, cross-referencing their old FSM/CRM system for the specifics when the ask references "how we had it" there. Use whenever the user asks to "configure the account off the kickoff call," "go through this transcript and set up what they asked for," "handle the config asks from the data review call," or hands over a transcript/call link for account setup/configuration work.
---

# Account Configuration (transcript → configuration asks → mocked-in setup)

Turns a customer call — a kickoff or a data-review call — into real settings
changes in the customer's live Podium account. Three phases, always in this
order:

1. **Get the transcript** — the user tells you which call each time (a
   pasted transcript, a Gong link, or a specific Salesforce activity).
2. **Extract the configuration asks** — read the whole thing, pull out
   every explicit "we want it set up like X" request, confirm the list
   with the user before touching anything.
3. **Implement by mocking in** — build each item in the customer's live
   Podium account via Mock, pulling the real specifics from their old FSM/
   CRM system when the ask referenced "how we had it there" rather than
   inventing values.

This is **not** the data-migration skill — it doesn't scrape, clean, or
push CSVs through the FSM Data Transformer wizard. It configures
*settings* (automations, notification routing, custom fields, business
units/job types, templates, permissions, integrations, review-request
rules, business hours, etc.), not entity data (contacts, jobs, invoices).
If a call transcript surfaces an actual data-migration ask ("also make
sure our old jobs come over"), flag it to the user as a separate
data-migration task rather than folding it in here.

**⚠️ Self-extending skill: every time you learn something new about where
a setting lives (in Podium or in a customer's old system) or hit a UI
quirk not already written down below, add it to the catalogs at the end
of this file before finishing the task.** This file is written to grow —
treat "I already knew that" as the exception, not "this file already
covers everything." See "Keeping this skill current" at the end.

## Milestone checkpoints

Whenever you complete a major milestone, or sub-task, STOP immediately. Do
not proceed to the next step. Instead, output the following message
exactly: "TASK COMPLETE: Please run /compact to clear the context before
we continue."

## Context: Lighthouse and Mocking in

**Lighthouse** (`lighthouse.podium.com`) is Podium's internal tool for
account/onboarding operations — it's how you get *to* a customer's
account, not where the actual product settings live. Every customer has a
Lighthouse location page
(`https://lighthouse.podium.com/locations/<org-uuid>/<location-id>`); ask
the user for it if you don't have it — it's customer-specific and not
guessable.

**"Mocking in"** means opening the customer's actual live product account
(`app.podium.com`) as if you were logged in as them, so you can click
around and change real settings — this is the only way to configure most
of what a kickoff/data-review call asks for; there is no API for this
skill.

1. From the Lighthouse location page, click the **hamburger (☰) menu**
   (top right, next to the clock/timezone) → **"Open Organization in
   Admin"** (may render as "Open Location in Admin" depending on the
   menu) → opens `admin.podium.com` for that org in a new tab.
2. On the admin org page, click **"Mock"** at the top right — **not**
   "Support Mock" (a separate, differently-logged tool). This opens a new
   tab on `app.podium.com`, logged into the customer's real account, with
   a yellow **"Mocked in as [name]"** banner (and a Sign out button).
   **Confirm the banner's account name matches the customer you're
   configuring before making any change** — see the drift warning below.
3. Every setting you touch here is a **live, shared production write** —
   the same account the customer's own staff use. Treat it accordingly
   (see "Caution" at the end).

**Known Mock-session gotchas** (carried over from the data-migration
skill — same underlying tool, same behavior):
- **Sessions drift to other customers.** The mocked session token expires
  after a few minutes; the next navigation can silently land you in a
  *different* customer's account. Before any write, re-check the top-left
  account name and the yellow banner match the target customer. If it
  drifted, close the tab and re-Mock fresh.
- **Lists don't always refresh live**, even across a hash-navigation
  reload — a change you just made can still show stale/missing in a
  long-lived Mock tab. Verify a write in a **fresh** Mock tab (full
  document reload) rather than trusting what a tab you've had open for a
  while shows.
- Safe rhythm: **re-Mock fresh → make your edits for this item → verify →
  re-Mock fresh again before the next batch** rather than staying in one
  tab for the whole session.

Load the core Chrome tools before starting if not already loaded:

```
ToolSearch("select:mcp__claude-in-chrome__tabs_context_mcp,mcp__claude-in-chrome__navigate,mcp__claude-in-chrome__computer,mcp__claude-in-chrome__read_page,mcp__claude-in-chrome__find,mcp__claude-in-chrome__get_page_text,mcp__claude-in-chrome__javascript_tool")
```

## Phase 1 — Get the transcript

**The input is always specified by the user** — which call, and how to
reach it. Don't assume; ask if it's ambiguous which call they mean
(kickoff vs. a later data-review call, or which of several calls). It
typically arrives as one of:

- **Pasted directly** in the conversation — read it as given.
- **A Gong call link** (`https://podium.app.gong.io/call?id=<n>`):
  1. `navigate` to the URL.
  2. **Okta gate:** this almost always redirects to `podium.okta.com`
     first — you cannot act on that domain. **Stop and ask the user to
     sign in via Okta**, wait, then re-navigate to the call URL.
  3. On the call page, click the small **">" chevron** at the left edge
     of the media panel to open the tab bar (Briefs / Outline /
     **Transcript** / Call Info / Points of interest / Slides), then
     click **"Transcript"**.
  4. `get_page_text` on the tab → read the persisted output (`Speaker \n
     m:ss \n text` blocks).
  5. **Long calls (>~45 min) truncate.** The rows are
     `.monologue-wrapper` elements — remove roughly the first half via
     `javascript_tool`, `get_page_text` again for the back half, overlap
     by a few rows, read both. (Same technique as the customer-audit
     skill's Phase D, if you want the full worked mechanics.)
- **A Salesforce Activity referencing a Gong call** — find the
  `gong.io/call?id=` link on the Case's Activity Timeline (Account →
  right-rail Activity panel), then follow the Gong steps above.

**Read the full transcript before moving to Phase 2** — a partial read
risks missing an ask made mid-call or in a wrap-up recap near the end.

## Phase 2 — Extract the configuration asks

Go through the transcript and pull out **every explicit configuration
request** — not just the headline items, and not things that only sound
like requests (a rep proposing an idea the customer didn't actually
confirm they want isn't an ask). Typical categories these calls surface
(not exhaustive — configuration surface area in Podium is broad):

- Business units, job types, trades/divisions
- Technicians/users and their roles/permissions (see the data-migration
  skill's "Prerequisite: get Business Units, Job Types, and Technicians
  into Podium" section for the exact user-creation mechanics if this
  overlaps with an in-flight migration — don't re-derive it here)
- Automations / workflows (e.g. review-request timing, follow-up
  sequences, missed-call texts)
- Message templates (SMS/email copy, signatures)
- Notification routing (who gets notified for what, and how)
- Custom fields / tags
- Business hours, holiday schedules
- Integrations (calendar, payment processor, other tools mentioned)
- Payment/invoicing settings (deposit requirements, accepted methods)
- Webchat/website widget behavior

For each ask, capture: **what they want, any specifics they gave
(exact wording, values, thresholds), and whether they referenced "like we
had it before/in [old system]"** — that last part is the signal to go
pull the real config from the old system in Phase 3 rather than guessing
a Podium-native equivalent.

**Flag, don't guess, on anything vague** ("something like what we had
before," "the usual setup," a request with no concrete value given). Note
it as needing the old-system lookup, or as needing a clarifying question
back to the user — never invent a threshold, wording, or business rule
the transcript didn't actually specify.

**⚠️ Confirm the extracted checklist with the user before building
anything.** This mirrors the data-migration skill's judgment-call rule:
every item you're about to write into a live, shared production account
gets a human check first — a misheard/misread ask here isn't a bad CSV
row you can re-run, it's a real setting the customer's team will work
under starting immediately. Present the list (what, source line/quote
from the transcript, and your plan for getting the exact values), and
get a go-ahead before Phase 3/4. The one exception: if the user has
already told you up front "just do everything in the transcript, don't
stop to check the list" — then skip the checklist-confirmation step, but
still pause on anything genuinely ambiguous or destructive per the
"Caution" section below.

## Phase 3 — Cross-reference the old system

For any ask that referenced "how we had it" in their old system, or
whose specifics weren't fully given on the call:

1. Get into the customer's old FSM/CRM using whatever credentials/access
   the user provides — **ask for them, never invent or guess**, same
   rule as the data-migration skill's scraper credentials.
2. **Verify you're in the correct customer's account before reading
   anything** — this browser is commonly signed into several different
   accounts on the same source system at once, and nothing forces the
   tab you're looking at to be the customer you're configuring. Confirm
   the account/company name shown in the source system's own UI (header,
   org switcher, settings page) before trusting anything you read there.
3. Locate the actual configuration screen and read the **real, live
   values** — the exact wording of a message template, the exact
   threshold on a follow-up delay, the exact list of job types/business
   units, etc. — rather than approximating from what the customer
   described verbally. People describe their own settings imprecisely on
   a call; the source system's config screen is the ground truth.
4. Check the **"Old-system reference map"** catalog at the end of this
   file first — if this FSM/CRM and this category of setting has already
   been located before, you already know where to look. If not, once
   you've found it, add an entry (see "Keeping this skill current").

## Phase 4 — Implement in Podium via Mock

1. Mock into the account (see "Context" above).
2. Build each confirmed item on the appropriate Podium settings page.
   Check the **"Podium settings locations & quirks"** catalog at the end
   of this file first for where a given category of setting lives and
   any known UI gotchas, before hunting for it blind.
3. **Match the old system's real values** (from Phase 3) exactly where
   the ask was "like we had it before" — don't paraphrase a template's
   wording or round a threshold "close enough."
4. **Verify each change persisted** before moving to the next item — per
   the Mock-session gotchas above, check in a fresh Mock tab rather than
   trusting a long-lived one.
5. Anything destructive, ambiguous, or account-wide in effect (e.g.
   changing a notification rule that affects every existing job, not
   just new ones) — confirm with the user before applying, per the
   skill-wide judgment-call rule below. A setting change is harder to
   silently undo than a bad CSV row: it actively changes how the
   customer's team is notified/paid/messaged starting the moment you
   save it.

## Keeping this skill current

**Whenever you learn something new during a session that isn't already
captured below — a settings page location, a UI gotcha, a mapping from
"customer said X" to "Podium calls this Y," or where a given piece of
config lives in a specific old FSM/CRM — add it to the relevant catalog
below before finishing the task, using `Edit` on this file directly.**
This is the same self-extending pattern the data-migration skill uses for
its "Known FSM data quirks catalog": the value compounds the more
FSMs/CRMs and Podium settings categories get documented, so treat writing
the learning down as part of finishing the task, not optional cleanup.

When you add an entry:
- Be specific (exact menu path, exact field name, exact old-system
  location) — a vague "check settings somewhere" entry isn't worth
  adding.
- Note the FSM/CRM it applies to for old-system entries; general Podium
  quirks apply regardless of source system.
- If you find an entry below is now wrong (Podium's UI moved, an old
  system's flow changed), **fix it in place** rather than leaving a
  stale row.

### Podium settings locations & quirks

*(Empty until a real session fills it in — mirror the data-migration
skill's Job Type / Business Unit / Technician entries as a model for the
level of detail expected: exact menu path, what the picker actually
looks like, any required-field gotchas, any bulk-creation shortcut worth
knowing about.)*

| Configuration category | Podium menu path | Notes / gotchas |
|---|---|---|
| *(none recorded yet)* | | |

### Old-system reference map

*(Where a given category of configuration lives in each source FSM/CRM —
add a row the first time you go look for something there. See the
data-migration skill's "Building the Membership Plans catalog" note for
the model: e.g. "ServiceTitan: Settings → Invoicing → Membership Types"
/ "HouseCall Pro: My Apps → Service plans → Plan templates".)*

| Source system | Configuration category | Where it lives | Notes |
|---|---|---|---|
| *(none recorded yet)* | | | |

## Caution

This writes directly into a **live, shared production account** other
people (the customer's staff, right now, and Podium's own CSM/onboarding
team) rely on — unlike a CSV re-upload, most of these changes take effect
immediately and aren't cleanly reversible by "just re-running" something.

- **Never invent a value the transcript or old system didn't actually
  provide.** A vague ask stays a question back to the user, not a guess.
- **Confirm the extracted checklist before building**, and confirm again
  before any individual change that's destructive, ambiguous, or affects
  existing customer-facing behavior account-wide (see Phase 4.5 above) —
  unless the user has explicitly said to proceed through the whole list
  without stopping.
- **Verify you're mocked into the correct customer** before every write,
  every time — not just once per session.
- Don't leave a Mock session logged in longer than needed; sign out when
  you're done with a customer's account.
