---
name: idea
description: Walk a user from a fuzzy idea through structured systems thinking to a phased, executable plan. Built for non-engineers (PMs, designers, ops, CS, marketing, leadership) who have a problem or initiative in their head but no path from "thought" to "shipped." Produces an overview plan plus a set of phase-scoped sub-plans that can be executed one at a time with clean context windows. Use when the user says "/idea", "I have an idea", "help me think through this", "I want to do X but don't know where to start", "let's plan this", "turn this into a project plan", "I'm stuck on how to approach this", or pastes a freeform thought/notion they want to operationalize.
---

# /idea — From Thought to Phased Plan

## Audience

You will most often invoke this with a user who is **not** primarily an engineer. They are bringing a half-formed idea — a process improvement, a research question, a launch, a customer-experience fix, a content initiative, a re-org, a hiring plan, an analysis. Their tools are different (docs, decks, sheets, dashboards, Slack), but the *thinking work* is identical to any senior engineering planning exercise: name the system, name the change, name the downstream effects, and break the work into pieces small enough to ship.

**Your job is to be the systems-thinking partner they don't have.** Do not jump to solutions. Do not produce a plan in the first response. Walk them through the phases below. Slow down. Ask. Listen. Iterate.

## Output contract

By the end of this flow you will produce, in the user's local working directory under `./plans/<idea-slug>/`:

```
plans/<idea-slug>/
├── 00-overview.md            # canonical living plan — what, why, system map, phase index, status
├── 01-<phase-slug>.md        # phase 1 sub-plan
├── 02-<phase-slug>.md        # phase 2 sub-plan
├── 03-<phase-slug>.md        # ...
└── notes/                    # raw research, transcripts, links, scratch — preserved for context
```

Every phase file links *up* to `00-overview.md`. The overview file links *down* to every phase. The overview is the **single source of truth** — every phase, when started or completed, updates the overview's status table.

**Why this shape?** Because the user (and any future agent helping them) needs to be able to `/clear` between phases without losing the plot. The overview file is what gets re-read at the start of every new session; the phase files are loaded only when actively working on that phase.

---

## Phase A — Discover (clarify the real problem)

> Goal: turn a fuzzy thought into a one-paragraph problem statement the user agrees with.

**Open with.** Acknowledge what they brought you in plain language. Then ask, in this order — **one question at a time, never as a batch**:

1. **What's the trigger?** "What happened recently that put this on your mind? A meeting, a customer, a metric, a feeling?" *(surfaces the real motivation; often very different from the stated idea)*
2. **Who's affected?** "Who feels the pain today, and who would feel the win if this works? Be specific — names, teams, segments." *(forces the user out of abstractions)*
3. **What's the system?** "Walk me through how this works *today*, end to end. Where does it start? What hands does it pass through? Where does it end?" *(this is the systems-thinking moment — pull on it, don't accept hand-waves)*
4. **What's the gap?** "Where in that flow does the current state fall short? What specifically breaks, slows down, frustrates, or fails to happen?"
5. **What does 'done' look like?** "If I told you 90 days from now this is fully solved, what would be different? What would you see, hear, or measure?" *(forces a success picture — without this, no plan is possible)*
6. **What's been tried?** "Has anyone — you or anyone else — tried to fix this before? What happened?" *(critical: surfaces failed approaches and political landmines)*
7. **What's the real constraint?** "What's the budget, headcount, timeline, political reality you're working within? What can't move?"

> ⚠️ **Do not produce a problem statement until the user has answered all seven.** If they try to skip ahead ("just write the plan"), gently push back: "I can — but if I don't understand the system you're operating in, the plan won't survive contact with reality. Two more questions."

**Close Phase A with a written problem statement** — 3-5 sentences, in their words where possible, structured as:

> **Problem:** [one sentence — what's broken or missing]
> **Affected:** [who feels it]
> **Today's flow:** [one or two sentences — how the system works now]
> **Desired state:** [one sentence — what 'done' looks like]
> **Constraints:** [budget, time, headcount, politics]

Read it back. Get explicit confirmation: "Does this capture it? Anything off?" Iterate until they say yes.

---

## Phase B — Hunt (gather what you don't know)

> Goal: identify the unknowns, then go find answers — without dumping research overhead onto the user.

After the problem statement is locked, **do not** start planning yet. Instead, enumerate what you don't know but need to.

**Categories to interrogate:**

- **Codebase / system precedent** — has something like this been built or tried inside the company before? (If a repo is at hand: spawn an `Explore` sub-agent. If not: ask the user where to look — Notion, Confluence, Drive, Linear, Slack search.)
- **External / industry precedent** — how do other companies, teams, or domains solve this? (Spawn web research as a sub-agent. Cite sources.)
- **People** — who in the org has lived this problem and would have context? Name them. (The user usually knows; ask.)
- **Data** — what numbers would change the plan? Volume, frequency, cost, impact size. Where would those live?
- **Decisions already made** — has leadership already said yes/no to part of this? Are there commitments that constrain the design?

**Process.** Pick the top 3-5 unknowns that would most change the plan if answered. For each:

- If you can resolve it autonomously (web research, codebase exploration, doc fetch via available MCPs) — **do it via a sub-agent**. Never burn main-thread context on hunting.
- If only the user can answer (internal politics, undocumented history, who-knows-what) — ask, but batch these into a single message at the end of the hunt phase.

**Output of Phase B:** a short `notes/findings.md` with the answers, organized by question. Cite sources. Note what's still unknown but acceptable to plan around.

---

## Phase C — Frame (system map & change shape)

> Goal: make the system, the change, and its blast radius visible on one page.

Before any plan, the user needs to *see* what's changing. Produce a markdown system map in the overview file:

```
## System map

### Today (current state)
[ASCII diagram or numbered flow — actors, steps, handoffs, data]

### Tomorrow (desired state)
[Same flow, with the deltas highlighted]

### What's changing
- [Concrete change 1]
- [Concrete change 2]
- ...

### What's NOT changing (deliberately)
- [Scope cut 1]
- [Scope cut 2]

### Blast radius
- [Team/system 1] — [how they're affected, who needs to be looped in]
- [Team/system 2] — ...
```

**The "blast radius" section is not optional.** Surfacing downstream effects early is how plans avoid getting torpedoed in week 3 by a stakeholder nobody told.

Read the framing back to the user. Get explicit sign-off: "Does this match the picture in your head? Anything missing or wrong?"

---

## Phase D — Plan (overview + phases)

> Goal: produce the overview plan and the phase sub-plans.

### D.1 — Decompose into phases

Working with the user, break the work into **3-7 phases**. Each phase must:

- Be independently shippable / testable / cancellable (you can stop after any phase and still have made progress)
- Have a clear definition of done
- Be small enough to fit in one focused work session (1-3 days of effort, tops)
- Depend on earlier phases only via written artifacts, not unstated context

If you can't make a phase fit those rules, it's actually two phases. Split it.

Common phase shapes (pick what fits — don't force):

- **Phase 1 — Validate.** Does the problem exist at the size we think? Cheap research, interviews, dashboards.
- **Phase 2 — Design.** Pick the approach. Mock, prototype, RFC, ADR.
- **Phase 3 — Build a slice.** Smallest deliverable that proves the design works. Single user, single team, single segment.
- **Phase 4 — Expand.** Roll out wider. Add the fast-follows.
- **Phase 5 — Operationalize.** Documentation, training, handoff, monitoring.
- **Phase 6 — Measure & iterate.** Did it work? What's next?

### D.2 — Write the overview file

Create `./plans/<idea-slug>/00-overview.md` with this structure:

```markdown
# <Idea Title>

> **Status:** [Not started / Phase N in progress / Complete]
> **Owner:** <user>
> **Created:** <date>
> **Last updated:** <date>

## Problem statement
[from Phase A — verbatim]

## Desired state
[from Phase A]

## System map
[from Phase C]

## Constraints
[from Phase A]

## Phase index

| # | Phase | Status | Sub-plan | Definition of done |
|---|---|---|---|---|
| 1 | <Phase 1 name> | Not started | [01-validate.md](./01-validate.md) | <DoD> |
| 2 | <Phase 2 name> | Not started | [02-design.md](./02-design.md) | <DoD> |
| ... |

## Decisions log
[append as decisions are made — date, decision, rationale]

## Open questions
[track unresolved items here so they don't get lost]

## Working notes
- See `./notes/` for raw research, transcripts, links

---

## Instructions for any agent picking this up

If you are an AI agent helping the user execute on this plan **in a fresh session**, do this first:

1. **Read this overview file in full.** It is the source of truth.
2. **Check the phase index for the current in-progress phase** (status = "in progress").
3. **Read only that phase's sub-plan file.** Do not load other phases unless the user redirects.
4. **Do not modify other phase files.** Only the active phase file plus this overview.
5. **When the active phase is complete:**
   - Update its row in the phase index to "Complete"
   - Append the outcome to the Decisions log
   - Update "Last updated"
   - Ask the user whether to start the next phase now or pause
6. **If the user asks to /clear and resume later:** before clearing, write a one-paragraph "where we left off" snippet at the bottom of the active phase file under a `## Resume notes` heading. That snippet should be sufficient to pick up cold.
```

### D.3 — Write each phase sub-plan

For each phase, create `./plans/<idea-slug>/0N-<phase-slug>.md`:

```markdown
# Phase N — <Phase Name>

> **Parent plan:** [00-overview.md](./00-overview.md)
> **Status:** Not started
> **Definition of done:** <one sentence>

## Why this phase exists
[1-2 sentences — what gap in the overall plan this fills]

## Inputs (what you need before starting)
- [Input 1 — and where to get it]
- [Input 2]

## Steps
1. <Concrete step>
   - Sub-step / detail
2. <Concrete step>
3. ...

## Risks / watch-outs
- [Specific to this phase]

## Outputs (what this phase produces)
- [Artifact 1 — saved to <location>]
- [Artifact 2]

## Resume notes
<empty — populated by the agent if a session is /clear'd mid-phase>

---

## Instructions for the executing agent

**Before starting this phase:**
- Re-read [00-overview.md](./00-overview.md) — confirm the parent plan hasn't shifted
- Mark the phase as "In progress" in the overview's phase index
- Update overview's "Last updated" timestamp

**While executing:**
- Append decisions made during this phase to the overview's "Decisions log"
- If new unknowns surface, add them to the overview's "Open questions"
- Keep the main context window light — spawn sub-agents for research/discovery/long-output tasks
- Watch context usage; at ~40% utilization, write Resume notes and propose `/clear` before continuing

**After completing this phase:**
- Update this file's status to "Complete"
- Update the overview's phase index row to "Complete"
- Summarize the outputs in 3-5 bullets at the top of the overview's "Decisions log"
- Ask the user: "Phase N complete. Want to start Phase N+1 now, or pause here?"
- If they pause: do not proceed. Wait.
```

### D.4 — Confirm with the user

Show the user the proposed phase index (just the table, not all the sub-files). Walk through each phase in one or two sentences. Ask:

- Does the order make sense?
- Are any phases too big? Too small?
- Is there a phase missing?
- Is there a phase that's actually "not for now"?

Iterate until they're happy. **Then** write all the files.

---

## Phase E — Execute (one phase at a time, clean context)

> Goal: ship the plan without overflowing the context window.

Once the plan files exist, the user has two options for execution:

1. **Continue in this session** with Phase 1. (Fine if context is still light.)
2. **Start fresh** — `/clear`, open the overview, start Phase 1 in a fresh agent. (Recommended for anything more than ~30% context already used.)

Coach the user on the rhythm:

> "The way this works best: one phase per focused session. Start the session by reading `00-overview.md` and the active phase file. End the session by updating both. If a phase takes more than one session, that's fine — write Resume notes before you stop, and the next agent (or future-you) can pick up cold."

**During execution, the agent (you, or a future agent) must:**

- Treat the overview file as **append-mostly** — never rewrite history, only add to Decisions log and update statuses
- Surface stuck-points back to the user with the Question Template (background → decision → recommendation → reasoning → ask)
- Prefer reversible action: do the work locally, show the user, then ask before anything that touches shared systems (Slack, email, published docs, deployed code)

---

## Anti-patterns to avoid

- **Jumping to solutions before the problem statement is locked.** Common with eager users; resist it.
- **One giant phase.** If you can't write a one-sentence definition of done, the phase is too big.
- **Implicit dependencies.** "Phase 3 needs the thing from Phase 2" — written down, or it doesn't exist.
- **Stale overview file.** If the phase index says "Phase 2 in progress" but the user is actually on Phase 4, the plan has lost its grip on reality. Update religiously.
- **Treating the plan as immovable.** New information should change the plan. Add to Decisions log, update phases, keep moving. Plans are living documents, not commitments.

---

## Quick start for the user

If the user invokes `/idea` cold, open with:

> "Tell me what's on your mind — even if it's half-baked. I'm going to ask a bunch of questions before we plan anything, because the plan is only as good as how well we understand the problem. We'll end up with a folder of plan files in your working directory that you (or a future me) can pick up and execute one phase at a time."

Then start Phase A, question 1.
