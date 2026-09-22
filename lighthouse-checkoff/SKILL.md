---
name: lighthouse-checkoff
description: Check off, skip, or mark N/A tasks on a customer's onboarding checklist in Podium's internal Lighthouse tool (lighthouse.podium.com), via Claude in Chrome browser automation. Use this whenever the user asks to "check off"/"complete"/"mark done" tasks in Lighthouse, update an onboarding plan/milestone progress, or mark Lighthouse tasks as Not Applicable (N/A) with a reason — including bulk requests like "check everything off except X" or "mark all Y tasks as N/A because Z."
---

# Lighthouse Checkoff

Automates completing, skipping, and marking-N/A tasks on a customer's
onboarding plan in Podium's internal tool, Lighthouse
(`https://lighthouse.podium.com/locations/<org-uuid>/<location-id>`,
**"Onboarding Steps (New)" tab**). Driven entirely through
`mcp__claude-in-chrome__*` browser automation tools — there is no API.

Load the core Chrome tools before starting if not already loaded:

```
ToolSearch("select:mcp__claude-in-chrome__tabs_context_mcp,mcp__claude-in-chrome__navigate,mcp__claude-in-chrome__computer,mcp__claude-in-chrome__read_page,mcp__claude-in-chrome__browser_batch,mcp__claude-in-chrome__get_page_text")
```

## Prerequisites

The user (or you) must already be on the correct customer's Lighthouse
location page, on the **"Onboarding Steps (New)"** tab. Use
`tabs_context_mcp` to find the tab; if none exists, ask the user to
navigate there first (the URL is customer-specific and not guessable).

## Page anatomy

- The plan is a list of **milestones** (collapsible sections), each with a
  "X of Y tasks done" progress bar. Click the chevron next to a milestone
  name to expand/collapse it.
- Each **task row** inside an expanded milestone has, left to right:
  - A **checkbox** — clicking it instantly marks the task **Complete**.
    No confirmation dialog. The row turns green, gets a "COMPLETE" badge
    next to the title, and the title gets strikethrough.
  - Visibility icon (green eye = visible to customer, red = hidden).
  - Owner icon (P = Podium, plain avatar = Customer, two-person icon =
    Together).
  - A note icon.
  - A **"⋮" (more actions) menu** with: "Change ownership", "Show/Hide to
    customer", and **"Mark N/A"**.
- **Marking a task N/A**: click "⋮" → "Mark N/A" → a modal titled "Mark
  task as not applicable" opens with a **required** "Task Note" textarea
  ("Add context for the onboarding team"). Type the reason, then click
  the **"Mark not applicable"** button. The row then shows an "N/A" badge
  and greyed text "This task counts toward progress and cannot be
  completed." N/A tasks count toward the milestone's completion
  percentage (unlike simply leaving a task unchecked).

## Workflow for bulk requests ("check off everything except X, mark Y as N/A because Z")

1. **Expand every milestone.** Scroll down clicking each collapsed
   section's chevron. Some may already be expanded by default.
2. **Get the full task list once**, via `get_page_text` on the tab (after
   expanding everything). This returns every task title + description
   across all milestones in one shot — use it to classify each task into
   "check off" / "skip" / "mark N/A (+ which reason)" per the user's
   criteria (e.g. tasks whose title contains "Socials:", or mentions
   "port"/"ported"). Do this classification fully before touching any
   checkboxes — do not guess mid-scroll.
3. **Scroll top-to-bottom through the real page**, screenshotting each
   viewport, and check off every visible task that should be checked
   (see "Reliability notes" below for click ordering). Skip the ones
   that should stay unchecked or need the N/A flow.
4. **Handle N/A tasks** via the "⋮" → "Mark N/A" → type reason → "Mark
   not applicable" flow, one task at a time (see below).
5. **Verify.** Scroll back to the top; the plan header shows "N / M
   milestones complete" and overall %. Each milestone header shows
   "X of Y tasks done" (and "· Z N/A" if applicable). Confirm milestones
   that should be 100% actually show COMPLETE, and any milestone with
   intentionally-skipped tasks shows the expected fractional count with
   those exact tasks still unchecked.

## Reliability notes (learned the hard way — follow these)

- **Checking a box can grow that row's height** if the title no longer
  fits on one line once the "COMPLETE" badge is appended — this shifts
  every row below it down, silently invalidating any coordinates you
  pre-computed for further checkbox clicks in the same batch.
  - **Fix: within one `browser_batch`, click checkboxes bottom-to-top**
    (last visible row first, moving upward). A shift only pushes rows
    that are already handled; rows still pending stay put.
- **Insert a ~1s `wait` between checkbox clicks.** Rapid consecutive
  clicks with no pause are sometimes silently dropped (the UI likely
  briefly disables interaction while the previous save request is
  in-flight). Even with bottom-to-top ordering and waits, a click can
  still occasionally fail.
- **Always re-screenshot and verify after every batch.** Compare the
  milestone's "X of Y tasks done" counter to how many you intended to
  check; re-click any row still showing an empty checkbox.
- **Don't scroll too far per step.** 4–6 scroll ticks is usually right;
  6+ risks skipping 1–4 rows past the bottom of the previous view.
  Scroll back up whenever you land past an unchecked row you haven't
  handled yet.
- `read_page`'s interactive-element dump only reflects what's currently
  rendered near the viewport (the list is effectively virtualized) — use
  it for locating buttons/menus in the current view, not as a source of
  truth for the full task list. Use `get_page_text` (after expanding all
  milestones) for the full-list classification pass instead.
- The N/A modal's textarea auto-focuses after the "Mark N/A" menu item
  is clicked once the modal renders — but click into the textarea before
  typing to be safe, and confirm the dialog's subtitle matches the task
  you meant to mark N/A before typing/submitting (menu positions shift
  as rows above them change height).

## Caution

This edits a **live, shared production record** other teammates (CSM, AE,
onboarding manager) rely on — checking a box marks real progress as done.
For bulk "check everything" style requests, the user's instructions
should unambiguously state which tasks to check, skip, or mark N/A (and
the N/A reason) before you start; if any task's category is unclear, ask
rather than guessing.
