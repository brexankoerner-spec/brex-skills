# Phase 4 — Refine & Operationalize

> **Parent plan:** [00-overview.md](./00-overview.md)
> **Status:** Not started
> **Definition of done:** Skill tuned based on real-world usage feedback; quarterly knowledge base refresh scheduled; Brexan is using it confidently as part of his workflow

## Why this phase exists

The first version of the skill will be good — but real-world use always surfaces gaps that testing doesn't catch. This phase is the "production hardening" pass: fix what's slightly off, lock in the refresh cadence, and make sure the skill is something Brexan reaches for naturally, not something he has to remember to use.

## Inputs (what you need before starting)

- Installed skill from Phase 3
- At least 1–2 weeks of real-world use (Brexan should have used the skill on several live submissions)
- Brexan's honest feedback on what felt right and what felt off

## Steps

1. **Collect feedback from real-world use**
   - What types of submissions is the skill most helpful on?
   - Are there situations where the output feels off-tone, overly cautious, or misses the mark?
   - Is the coaching teaching Brexan over time, or does he feel like he's reading the same suggestions repeatedly?
   - Any guardrail misfires? (e.g., being too conservative when a firm stance was appropriate)

2. **Tune the SKILL.md based on feedback**
   - Update guardrail language if needed
   - Refine coaching note templates if they're feeling formulaic
   - Add any new submission type patterns that emerged from real use

3. **Schedule the quarterly knowledge base refresh**
   - Set a recurring reminder or scheduled task for approximately every 90 days
   - The refresh involves re-running Phase 1 (just the Slack read and pattern extraction) — not rebuilding the whole skill
   - The refresh window should roll forward: always the most recent 90 days
   - Update `./notes/best-practices.md` with new patterns, don't wipe the old ones — append and note the date

4. **Document the invocation pattern for future-Brexan**
   - Write a short "how to use this skill" note in the overview so that in 3 months, Brexan (or a fresh agent) can pick it up cold
   - Include: what to provide, what to expect back, when to use it vs. when to just post

## Risks / watch-outs

- If Brexan stops using the skill after Phase 3, that's signal — find out why before this phase closes. It either means the output isn't useful or the friction of invoking it is too high.
- The knowledge base will go stale if the refresh doesn't happen. Calendar it explicitly.
- Don't over-tune — if the skill is mostly working, resist the urge to rewrite it. Small targeted adjustments only.

## Outputs (what this phase produces)

- Refined `SKILL.md`
- Updated `./notes/best-practices.md` with real-world pattern additions
- Quarterly refresh scheduled
- Short "how to use" section added to `00-overview.md`

## Resume notes

*(Populated by the agent if a session is cleared mid-phase)*

---

## Instructions for the executing agent

**Before starting this phase:**
- Re-read [00-overview.md](./00-overview.md)
- Confirm Phase 3 is complete and the skill has been used on real submissions
- Ask Brexan for honest feedback before making any changes

**While executing:**
- Only modify the SKILL.md and best-practices.md — do not restructure the plan files
- Append all tuning decisions to the overview's Decisions log with rationale
- When scheduling the quarterly refresh, note the target date in the Decisions log

**After completing this phase:**
- Update this file's status to "Complete"
- Update the overview's phase index to "Complete"
- Update overview status to "Complete"
- Tell Brexan: "All four phases done. The skill is live, tuned, and on a quarterly refresh schedule. Next refresh due: [date]."
