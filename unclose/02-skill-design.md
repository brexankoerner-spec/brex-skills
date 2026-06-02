# Phase 2 — Skill Design

> **Parent plan:** [00-overview.md](./00-overview.md)
> **Status:** Complete
> **Definition of done:** A complete `SKILL.md` file written and reviewed by Brexan, covering invocation format, coaching logic, output structure, and all guardrails

## Why this phase exists

The SKILL.md is the brain of the skill — it tells any future agent exactly how to behave when Brexan invokes it. Without a well-designed SKILL.md, the skill will produce inconsistent results, miss important context, or fail to coach in the right direction. This phase locks the design before any code or logic is written.

## Inputs (what you need before starting)

- `./notes/best-practices.md` (from Phase 1) — must be complete
- Confirmed submission types and their distinct coaching postures (from Phase 1)
- Brexan's stated constraints: no cancellation advocacy, professional/executive tone, action ownership emphasis

## Steps

1. **Define the invocation contract**
   - What exactly does Brexan say to invoke the skill? (e.g., "Review my unclose response" + thread link + draft)
   - What if he has no draft? (skill should be able to generate a starting point)
   - What if the thread is mid-conversation vs. a fresh submission? (skill should detect this and adjust)

2. **Design the skill's intake logic**
   - Step 1: Skill receives a Slack thread link → extracts channel ID and message TS
   - Step 2: Reads the original submission notification to identify submission type
   - Step 3: Reads the full thread to understand current state (if mid-conversation)
   - Step 4: Loads the relevant section of `best-practices.md` for that submission type
   - Step 5: Reviews Brexan's draft (or generates one if none provided)

3. **Design the coaching output format**
   The skill should return two things, clearly separated:
   - **Revised response** — clean, ready-to-post version of Brexan's draft
   - **Coaching notes** — bullet-by-bullet explanation of every change made and why, referencing specific principles (e.g., "Changed 'I'm not sure what the next step is' to 'I'll connect with the AE by EOD Thursday and report back' — removes ambiguity and signals ownership")

4. **Write the guardrails into the SKILL.md**
   - Never recommend cancellation unless the submission explicitly states an obvious impasse (business closing, customer unreachable after 10+ attempts, confirmed product incompatibility with no workaround)
   - Always maintain professional, executive-ready tone — no casual language, no venting
   - Keep revised responses concise — if Brexan's draft is long, the skill should tighten it, not expand it
   - Never make up account details or fabricate context not present in the thread

5. **Review the draft SKILL.md with Brexan**
   - Present the invocation format and output structure
   - Confirm the guardrails feel right
   - Confirm the coaching note style feels like teaching, not just correcting

## Risks / watch-outs

- The skill needs to handle two modes cleanly: (a) initial response to a new submission, (b) follow-up in an ongoing thread. These have different coaching postures — don't conflate them.
- The best-practices doc needs to fit in context alongside the thread content — if it's too long, it needs to be summarized or chunked by type.
- Avoid over-engineering the output — the revised response should feel like Brexan wrote it, not like a legal memo.

## Outputs (what this phase produces)

- `SKILL.md` — complete skill definition, saved to the appropriate skills directory
- Updated overview Decisions log with any design choices made

## Resume notes

*(Populated by the agent if a session is cleared mid-phase)*

---

## Instructions for the executing agent

**Before starting this phase:**
- Re-read [00-overview.md](./00-overview.md) — confirm the parent plan hasn't shifted
- Read `./notes/best-practices.md` in full before designing the skill logic
- Mark this phase as "In progress" in the overview's phase index
- Update overview's "Last updated" timestamp

**While executing:**
- Draft the SKILL.md in `/sessions/.../mnt/outputs/plans/unclose-coaching-skill/` first — show Brexan before moving it to the live skills directory
- Append design decisions to the overview's Decisions log
- If the best-practices doc is too long to fit in context, note this as a design constraint and propose a chunking strategy

**After completing this phase:**
- Update this file's status to "Complete"
- Update the overview's phase index row to "Complete"
- Ask Brexan: "Phase 2 complete — SKILL.md is ready. Want to move to Phase 3 and build it?"
