# Email Gamification Skill

**Version: V1.5**
_Increment this version number every time this skill is modified. Format: V{major}.{minor} — bump minor for refinements, major for structural changes._

Scan Brexan's Gmail inbox, score each unread email by urgency and age, then deliver a prioritized scorecard via Slack DM and a push notification summary. Claude reads and scores only — never sends or responds to any email.

---

## Configuration

- **Gmail account:** brexan.koerner@podium.com
- **Slack channel ID:** C0B2H7KSCEP
- **State file:** ~/.claude/skills/email-gamification/state.json *(used in Phase 4 — skip if not present)*

---

## Privacy Rules (non-negotiable)

- **Body content is read for scoring and display** — call `get_thread` on emails that pass initial metadata filter.
- **Never include body content in push notifications** — push notifications go to macOS and must remain subject-line only.
- **Strip before displaying in Slack:** remove signatures, quoted reply chains, image placeholders (`[cid:...]`), and raw URLs. Keep actual message content only.
- The Gmail API returns a `snippet` field — ignore it. Always use `get_thread` with `FULL_CONTENT` for accurate body access.

---

## Pipeline

### Step 1 — Fetch Emails

**Pass 1 — Metadata search:**
Search Gmail with:
```
is:unread -category:promotions -category:social in:inbox
```
- Max 50 results
- From each thread, extract: thread ID, subject, sender, toRecipients, ccRecipients, date/timestamp, label list
- Do NOT read or reference the `snippet` field

**Pass 2 — Body fetch for candidates:**
After initial metadata scoring (Step 2A), call `get_thread` with `messageFormat: FULL_CONTENT` for every email with a metadata score ≥ 5. This avoids fetching body content for clearly irrelevant emails while ensuring body is available for all realistic candidates.

---

### Step 2 — Score Each Email

Scoring runs in two passes: metadata first, then body refinement.

---

#### Step 2A — Metadata Score (subject, sender, recipients, timestamps)

##### A. Base Score

**Default: +10** — any email where Brexan is in `toRecipients` and none of the skip conditions below apply.

**SKIP (exclude from report entirely) if any of the following match:**

| Skip Condition | Examples |
|---|---|
| Brexan is only in `ccRecipients` | — |
| Sender is Brexan's own address (`brexan.koerner@podium.com`) | Google follow-up nudge on unread sent mail |
| Sender address is clearly automated | `noreply@`, `no-reply@`, `donotreply@`, `notifications@`, `alerts@`, `system@`, `mailer@`, `bounce@` |
| Subject matches a structured/templated pattern | Starts with `[Tag]` (e.g. `[Jira]`, `[GitHub]`, `[Alert]`); contains "Invoice #", "Order #", "Receipt", "Confirmation #", "Tracking", "Your payment", "Password reset", "Verification code", "Security alert"; calendar responses ("Accepted:", "Declined:", "Invitation:", "Updated invitation:") |
| Subject or sender signals marketing/promotional content | "Unsubscribe", "% off", "Deal", "Offer expires", "Newsletter", "Your weekly digest" |

If no skip condition matches → base score **+10**, proceed to Part B.
If any skip condition matches → **SKIP**, do not include in report.

##### B. Urgency Bonus — subject only (pick exactly one, add to base)

| Signal | Points |
|---|---|
| Explicit deadline, time-sensitive language ("urgent", "ASAP", "by EOD", "by Friday", "deadline", "expiring", "overdue", "time-sensitive", "critical", "escalat") | +20 |
| Customer complaint or issue ("complaint", "unhappy", "disappointed", "frustrated", "issue", "problem", "not working", "broken", "wrong", "error", "refund", "cancel") | +15 |
| Internal request needing response ("can you", "could you", "please", "requesting", "need your", "waiting on", "following up", "reminder", "FYI action") | +10 |
| Low urgency, ambiguous, or informational | +5 |

##### C. Age Penalty (add to running total)

- Calculate calendar days since the email was received
- Add **+10 points per day** the email has been sitting unread
- Same-day email gets +0

Emails with metadata score ≥ 5 proceed to Step 2B. All others are excluded.

---

#### Step 2B — Body Urgency Modifier (requires `get_thread` body content)

Read the most recent message body. Apply **one** modifier based on what the body actually reveals — this can upgrade OR downgrade the metadata score:

| Body reveals | Modifier |
|---|---|
| Explicit deadline, escalation, legal/financial risk, executive involvement, customer threatening to leave | +15 |
| Clear ask with specific action required, frustration or urgency in tone, multiple people waiting on Brexan | +10 |
| Friendly request, no hard deadline, informational with a soft ask | +0 |
| Subject implied urgency but body is routine, automated, or informational (subject was misleading) | −10 |
| Email is clearly spam, out-of-office, automated notification, or no action needed despite subject | Remove from report entirely |

#### D. Final Filter

- Include only emails with **final score ≥ 10** after both passes
- Emails scored 0 (CC/auto/skipped) are excluded — count them for the footer

---

### Step 3 — Sort and Bucket

Sort all flagged emails descending by score.

Assign emoji bucket:
- 🔴 **Critical** — score ≥ 30
- 🟠 **Needs attention** — score 20–29
- 🟡 **On your radar** — score 10–19

---

### Step 4 — Fire Push Notification *(local sessions only)*

> **Note:** The `PushNotification` tool only works in a local Claude Code session. Remote/CCR scheduled runs cannot reach macOS — skip this step entirely when running as a scheduled routine. Do not error; continue to Step 5.

Send a push notification with this format (under 200 characters):

```
📬 Inbox score: {total} · 🔴 {n} · 🟠 {n} · 🟡 {n} · Check Slack for details.
```

If inbox is clean (0 flagged emails):
```
📬 Clean inbox · 0 emails need attention · Nice work.
```

---

### Step 5 — Prepare Top 3 for Display

Body content is already fetched from Step 2B — no additional API calls needed. From the sorted final list, take the top 3 highest-scoring emails and prepare their display content:

- **#1 (highest score):** Use the most recent message's cleaned full body. Strip signatures, quoted reply chains, image placeholders (`[cid:...]`), and link URLs.
- **#2 and #3:** Write a 1–2 sentence summary of the most recent message. Focus on what's being asked and what action is needed.

If fewer than 3 emails are flagged, apply this to however many exist.

### Step 6 — Send Slack DM to Self

Send to channel ID `C0B2H7KSCEP`.

#### Format — emails found:

```
📬 *Inbox Scorecard — {Day, Mon DD} · {AM/PM}*
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total score: *{X} pts* · {N} email(s) flagged
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔴 *Critical (30+ pts)*

*1. {Subject}* — {Sender} · {X} pts · {N} day(s) old
>{Full cleaned body of email #1}

*2. {Subject}* — {Sender} · {X} pts · {N} day(s) old
>{1–2 sentence summary}

*3. {Subject}* — {Sender} · {X} pts · {N} day(s) old
>{1–2 sentence summary}

🟠 *Needs Attention (20–29 pts)*
• *{Subject}* — {Sender} · {X} pts · {N} day(s) old

🟡 *On Your Radar (10–19 pts)*
• *{Subject}* — {Sender} · {X} pts · {N} day(s) old

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
_Scanned {N} emails · {N} skipped (CC / automated / no action needed)_
_Scoring: base (+10 action needed) + urgency (+5–20) + age (+10/day unread)_
```

- Top 3 are numbered with body/summary inline. Emails #4+ are bullet points only — no body content.
- If a bucket has 0 emails, omit it entirely.
- Show sender as first name + domain (e.g. "Sherri · dormannsheatingandcooling.com") — never raw addresses only.
- Strip all signatures, quoted chains, image tags, and URLs from body before including in Slack.

#### Format — clean inbox:

```
📬 *Inbox Scorecard — {Day, Mon DD} · {AM/PM}*
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ *Clean inbox* — nothing needs your attention right now.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
_Scanned {N} emails · all skipped (CC / automated / no action needed)_
```

---

### Step 6 — Complete

Output a brief plain-text completion note (visible in Claude Code task log only — not sent anywhere):

```
Email review complete — {N} flagged · Total score: {X} pts · Slack DM sent · Push notification fired.
```

---

## Error Handling

- If Gmail search returns 0 results: send clean inbox message to Slack + push notification. Do not error.
- If Slack DM fails: note the failure in the completion log. Do not retry automatically.
- If push notification is suppressed (terminal has focus): this is expected — log it and continue.
- Never expose raw error messages containing email content in any output.
