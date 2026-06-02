# Unclose Response Coaching Skill

> **Status:** In progress — Phase 2
> **Owner:** Brexan Koerner
> **Created:** 2026-05-19
> **Last updated:** 2026-05-19

## Problem statement

Brexan's responses in the `#unclose-at-risk` channel are competent but not yet projecting the level of ownership, confidence, and decisiveness that would distinguish him as a high-performing OM in front of upper management. Responses sometimes lean toward passive status updates rather than clear action ownership, and can lack the directness that signals "I've got this" to the managers who monitor these threads. The goal is not to fix a problem — it's to go from good to great to stellar.

## Desired state

Brexan is known as the OM who has a plan, owns his accounts, and doesn't create work for management. His posts are concise, direct, and confident. When management reads a thread he's active in, the impression is that the situation is handled. He is being noticed as a mover — proactive, accountable, and competent.

## System map

### Today (current state)
```
New submission drops in #unclose-at-risk
        ↓
Brexan reads the notification + any existing thread context
        ↓
Brexan drafts a response (or hesitates, unsure of best approach)
        ↓
Posts in thread → management reads → sometimes questions or redirects
        ↓
Brexan follows up over days/weeks as situation evolves
```

### Tomorrow (desired state)
```
New submission drops in #unclose-at-risk
        ↓
Brexan reads it + optionally drafts a response
        ↓
Calls the unclose skill → provides thread link + draft (or just the link)
        ↓
Skill identifies submission type, reads thread context, references best practices knowledge base
        ↓
Returns: revised response + coaching notes explaining every suggested change
        ↓
Brexan posts the improved response with confidence
```

### What's changing
- Brexan has a coaching layer before posting, backed by 90 days of real channel history
- Best practices are systematically extracted and applied, not guessed at

### What's NOT changing
- Brexan owns every decision — the skill advises, never overrides
- He still reads the situation and determines the path forward
- The channel itself is unchanged — this is entirely Brexan-side

### Blast radius
- **Brexan only** — no system integrations, no changes to the channel, no other team members impacted
- Low risk, fully reversible

## Constraints

- The skill must **never lean toward recommending cancellation** unless the situation is an obvious impasse with no viable path forward
- On-demand invocation only — Brexan provides a Slack thread link and either a draft response or a request for help drafting
- Tone must be **professional and executive-ready** — these threads are monitored by upper management
- Knowledge base to be refreshed **quarterly** (not on every use)

## Phase index

| # | Phase | Status | Sub-plan | Definition of done |
|---|---|---|---|---|
| 1 | Knowledge Base Build | Complete | [01-knowledge-base-build.md](./01-knowledge-base-build.md) | 90-day Slack history read, threads sampled, best practices doc saved by submission type |
| 2 | Skill Design | Complete | [02-skill-design.md](./02-skill-design.md) | SKILL.md written with coaching logic, input format, output structure, and guardrails |
| 3 | Build & Test | Complete | [03-build-and-test.md](./03-build-and-test.md) | Skill functional and tested on 3 real submissions with coaching output confirmed useful |
| 4 | Refine & Operationalize | Not started | [04-refine-and-operationalize.md](./04-refine-and-operationalize.md) | Skill tuned based on test results, quarterly refresh scheduled |

## Decisions log

- **2026-05-19** — Knowledge base window set to 90 days (not 30). Rationale: richer pattern set, low additional cost (~$0.50–$1.00 total).
- **2026-05-19** — Knowledge base refresh cadence set to quarterly. Rationale: sufficient to capture evolving norms without over-engineering.
- **2026-05-19** — Skill is on-demand only (not automated). Rationale: Brexan wants to review and approve every response before posting.
- **2026-05-19** — Phase 3 complete. Tested on 2 live threads (Kimbro Air — Product Fit FOLLOW-UP; Ascend HVAC — Unfit Business FOLLOW-UP x2). Key refinements: (1) added Potts two-tier management framework and 5-question review criteria to SKILL.md and best-practices.md; (2) capped em-dash usage at one per response in voice guardrail. Skill packaged as `unclose.skill` and ready to install.
- **2026-05-19** — Phase 3 mid-test addition: Two-tier management structure confirmed (Alex Howe = direct manager/active collaborator, Robert Potts = final approver/intermittent on large accounts). Potts's 5-question review framework added to SKILL.md as a calibration layer and to best-practices.md as Universal Principle 7. Framework applied differently by moment: submission fields address Q1–Q2, mid-thread updates address Q3, resolution posts address all 5.
- **2026-05-19** — Phase 2 design decisions: (1) Single skill handles both modes — INITIAL SUBMISSION and FOLLOW-UP — via explicit label from Brexan. (2) Best-practices.md loaded by submission type at runtime (relevant section + Universal Principles only) to keep context usage manageable. (3) Output always two sections: REVISED RESPONSE (clean, ready-to-post) + COACHING NOTES (bullet-by-bullet with principle references). (4) Coaching notes teach the why, not just flag what changed. (5) Seven guardrails codified: no cancellation advocacy, executive-ready tone, tighten not expand, no fabrication, Brexan's voice, teaching notes, align with management directives. SKILL.md saved to `./SKILL.md`.
- **2026-05-19** — Phase 1 complete. Key findings: (1) 6 submission types confirmed — Misset (155) and Product Fit (150) are the top two, together accounting for 51% of all submissions. (2) Strong OM responses are built on documented outreach logs, specific AE asks, and proactive thread updates — not just effort. (3) The bot submission fields themselves are the first impression — weak submissions lead with vague or empty fields. (4) Reviewer routing appears to have shifted ~spring 2026: John Palfreyman and Sam Skanchy now primary on Misset/Product Fit; Than Hancock still active on Delinquent. (5) Automated "At-Risk Alert" messages (283 total) are billing bot notifications — distinct from formal submissions. Full knowledge base saved to `./notes/best-practices.md`.

## Open questions

- Which submission types should be treated as distinct coaching buckets? (Identified so far: Product Fit, Unfit Business, Unresponsive, Delinquent Billing — confirm during Phase 1.)
- Should the skill handle mid-thread follow-up responses differently from initial responses? (Likely yes — confirm during Phase 2.)

## Working notes
- See `./notes/findings.md` for research from the discovery phase
- Slack channel: `#unclose-at-risk` (ID: `C07TZG7K7DZ`)

---

## Instructions for any agent picking this up

If you are an AI agent helping Brexan execute on this plan in a fresh session, do this first:

1. **Read this overview file in full.** It is the source of truth.
2. **Check the phase index for the current in-progress phase** (status = "In progress").
3. **Read only that phase's sub-plan file.** Do not load other phases unless Brexan redirects.
4. **Do not modify other phase files.** Only the active phase file plus this overview.
5. **When the active phase is complete:**
   - Update its row in the phase index to "Complete"
   - Append the outcome to the Decisions log
   - Update "Last updated"
   - Ask Brexan whether to start the next phase now or pause
6. **If Brexan asks to /clear and resume later:** before clearing, write a one-paragraph "where we left off" snippet at the bottom of the active phase file under a `## Resume notes` heading.
