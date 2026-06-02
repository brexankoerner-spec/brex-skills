# Phase 3 — Build & Test

> **Parent plan:** [00-overview.md](./00-overview.md)
> **Status:** Complete
> **Definition of done:** Skill is installed and functional; tested on 3 real submissions from the channel; Brexan confirms the coaching output is genuinely useful

## Why this phase exists

A SKILL.md that looks good on paper may still produce coaching that feels off — too generic, too formal, misreads the situation. This phase proves the skill works in the real world by running it against actual submissions and iterating until the output is something Brexan would actually use.

## Inputs (what you need before starting)

- Completed `SKILL.md` from Phase 2
- `./notes/best-practices.md` from Phase 1
- 3 real submission thread links from `#unclose-at-risk` (ideally one per common type: Product Fit, Unfit Business, Unresponsive)

## Steps

1. **Install the skill**
   - Move the `SKILL.md` to the correct skills directory so it's invocable
   - Confirm the skill appears in the available skills list

2. **Select 3 test submissions**
   - Pull one from each of the primary submission types (Product Fit, Unfit Business, Unresponsive)
   - Ideally: one where Brexan has an existing draft to review, one where he needs a response generated from scratch
   - These can be live current submissions or recent ones from the channel

3. **Run the skill on each test submission**
   - For each: provide the thread link + a draft (or request for a drafted response)
   - Capture the full output: revised response + coaching notes

4. **Evaluate output quality with Brexan**
   For each test run, assess:
   - Does the revised response sound like a stronger version of Brexan — not a different person?
   - Are the coaching notes genuinely teachable? Does Brexan understand *why* each change was made?
   - Is the tone executive-ready without being stiff?
   - Did the skill correctly identify the submission type and apply the right coaching posture?
   - Did the skill ever stray toward cancellation advocacy when it shouldn't have?

5. **Iterate on the SKILL.md based on findings**
   - If the tone is off, adjust the guardrail language
   - If coaching notes feel generic, add more specific pattern examples from the best practices doc
   - If the skill misidentifies submission types, improve the intake logic
   - Re-test after each adjustment

## Risks / watch-outs

- Real submissions may have sensitive account details — use judgment about what to share in the test run
- "Useful" is Brexan's call, not the skill's. If he wouldn't post the revised response, the test failed.
- Don't declare this phase done after one successful run — three different submission types is the bar

## Outputs (what this phase produces)

- Installed, functional skill in the skills directory
- Test run notes (what worked, what was adjusted) appended to `./notes/findings.md`
- Updated `SKILL.md` reflecting any refinements from testing

## Resume notes

*(Populated by the agent if a session is cleared mid-phase)*

---

## Instructions for the executing agent

**Before starting this phase:**
- Re-read [00-overview.md](./00-overview.md) — confirm the parent plan hasn't shifted
- Confirm the SKILL.md from Phase 2 is finalized and approved by Brexan
- Mark this phase as "In progress" in the overview's phase index

**While executing:**
- Do not post anything to Slack on Brexan's behalf — present output for his review only
- Log each test run result in `./notes/findings.md`
- If a test run reveals a fundamental design flaw, escalate to Brexan before continuing — do not silently patch

**After completing this phase:**
- Update this file's status to "Complete"
- Update the overview's phase index row to "Complete"
- Summarize what was learned from testing in the Decisions log
- Ask Brexan: "Phase 3 complete — skill is live and tested. Want to move to Phase 4 to operationalize it?"
