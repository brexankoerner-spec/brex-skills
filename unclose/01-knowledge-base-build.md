# Phase 1 — Knowledge Base Build

> **Parent plan:** [00-overview.md](./00-overview.md)
> **Status:** Complete
> **Definition of done:** 90-day Slack history read, threads sampled by submission type, and a structured best practices document saved to `./notes/best-practices.md`

## Why this phase exists

The coaching skill is only as good as what it learned from. Before writing a single line of skill logic, we need a reference document that captures real patterns from the channel — what strong responses look like, what weak ones look like, how different submission types should be handled, and what moves the needle toward resolution. This phase produces that document.

## Inputs (what you need before starting)

- Access to the Slack MCP (already confirmed connected)
- Channel ID: `C07TZG7K7DZ` (`#unclose-at-risk`)
- 90-day window: approximately Feb 18, 2026 → May 19, 2026 (unix: `1739836800` → `1747699200`)

## Steps

1. **Paginate through 90 days of top-level channel messages**
   - Use `slack_read_channel` with `oldest` timestamp for 90 days ago
   - Paginate using the `cursor` from each response until all messages are retrieved
   - Log each submission notification: account name, submission type, thread reply count, message TS

2. **Categorize submissions by type**
   - Identify the four primary types observed: Product Fit, Unfit Business, Unresponsive, Delinquent Billing
   - Note: there may be additional or hybrid types — flag them if found
   - Build a simple inventory: type → list of message TSs

3. **Sample threads strategically**
   - For each submission type, pull 3–5 threads using `slack_read_thread` — prioritize threads with higher reply counts (more evolved conversations = more patterns)
   - Focus on threads where a clear resolution was reached (positive or negative) — these have the most signal
   - Note: do NOT read every thread — this is a sampling exercise, not exhaustive coverage

4. **Extract patterns per submission type**
   For each type, identify:
   - What does a strong opening OM response look like? (tone, length, structure, action ownership)
   - What does a weak opening response look like? (vague, passive, creates work for others)
   - What kinds of follow-up moves advance the situation? (specific asks, clear timelines, looping in the right people)
   - What language signals ownership vs. uncertainty?
   - Are there situations where acknowledging a likely cancellation is appropriate? How is it handled without advocating for it?

5. **Write `./notes/best-practices.md`**
   - Organize by submission type
   - Include real (anonymized if needed) example phrases — both strong and weak
   - Add a "universal principles" section covering tone, structure, and escalation awareness that applies across all types

## Risks / watch-outs

- Some older threads may reflect a different review process (older submissions reference "Than and Chance" as reviewers — this process may have changed). Note any format changes observed.
- Thread sampling must stay representative — don't over-index on one submission type just because it has more replies.
- The goal is patterns, not transcripts. Keep the best practices doc concise — it needs to fit in context when the skill runs.

## Outputs (what this phase produces)

- `./notes/best-practices.md` — structured best practices by submission type, with example phrases and universal principles
- Updated `./notes/findings.md` — any new findings about channel structure or submission patterns worth recording

## Resume notes

*(Populated by the agent if a session is cleared mid-phase)*

---

## Instructions for the executing agent

**Before starting this phase:**
- Re-read [00-overview.md](./00-overview.md) — confirm the parent plan hasn't shifted
- Mark this phase as "In progress" in the overview's phase index
- Update overview's "Last updated" timestamp

**While executing:**
- Spawn sub-agents for long Slack reads to avoid burning main-thread context
- Append decisions made during this phase to the overview's Decisions log
- If new submission types are discovered, add them to the overview's Open questions
- At ~40% context utilization, write Resume notes and propose a `/clear` before continuing

**After completing this phase:**
- Update this file's status to "Complete"
- Update the overview's phase index row to "Complete"
- Summarize the key patterns found (3–5 bullets) in the overview's Decisions log
- Ask Brexan: "Phase 1 complete — want to start Phase 2 now, or review the best practices doc first?"
