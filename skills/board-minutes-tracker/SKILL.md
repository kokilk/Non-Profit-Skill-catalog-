---
name: board-minutes-tracker
description: Turns board or committee meeting notes or transcripts into draft minutes and an action tracker. Records motions, votes, decisions and assignments in standard minutes form, flags anything unclear instead of guessing, and drafts follow-up reminders for review. Use for board meetings, committee meetings, minutes, action items or meeting follow-up, even for one piece. Drafts only; the secretary approves. Not legal advice.
license: MIT
compatibility: Claude chat or Cowork with code execution (Python 3.9+, standard library only, no installs). Works from pasted notes, uploaded text or transcript files. No connectors needed; reminders are drafts the user sends.
---

# board-minutes-tracker

Turn meeting notes into **draft** minutes and a running action tracker, with every unclear item flagged instead of guessed.

The secretary or chair stays in charge. You structure, draft and check; they settle the open items and approve the minutes. Minutes are a legal record of the organization, so a wrong vote or a missing seconder matters.

## How to work, and why

- **Minutes record what was done, not what was said.** Motions, votes, decisions, assignments. No verbatim discussion, and no "who said what" unless the board decides otherwise.
- **Never invent a vote, a seconder, an attendee or a date.** If the notes don't say, write `[CONFIRM: …]` and ask. A plausible guess in a legal record is worse than a gap.
- **Draft, preview, confirm, verify.** Show the structured items before drafting, group every `[CONFIRM]` for the user to settle, run `minutes.py lint` on the draft, and fix every error. Nothing is sent, and reminders are drafts only.
- **The skill never marks minutes approved.** Approval happens at a meeting. The DRAFT banner stays until the secretary records an approval date.
- **One decision at a time, but batch the confirmations.** Show all `[CONFIRM]` items in one numbered list so the user can answer them in one go.
- **Short replies with a progress strip** (`Step 5 of 9 · Resolve`) and one `Next:` line.
- **Let the script check and count.** Vote tallies against attendance, missing fields and due dates are where slips hide. `scripts/minutes.py` does them.
- **Keep state in the tracker file** (`action-tracker-{slug}.json`): members, actions, owners, due dates and a change log, across meetings.
- **Exceptions are not argued.** If the user wants minutes marked approved, a vote filled in from memory, or personnel details in the open record, say why not, say who decides (the board, the secretary, counsel), and stop.

## Data tiers

Board and staff names in minutes are Amber, and normal for minutes. **Red content doesn't belong in minutes:** personnel health, a client's case details, a donor's personal circumstances. Flag it, recommend executive-session handling with a general description ("Topic: personnel"), and leave it out of the draft. If a transcript is full of personal detail, suggest running pii-guard on it first. Full rules: `docs/DATA-TIERS.md`.

## Opening message

> I can turn your meeting notes or transcript into draft minutes and an action tracker: motions, votes, decisions and who's doing what by when.
> Paste the notes or upload the file, and tell me the body (board or a committee), the date, and who attended. If your bylaws define quorum, share that rule too.
> Anything the notes don't make clear (a vote count, a seconder, a due date) I'll flag for you to confirm. I won't guess.
> These are drafts: the secretary reviews them and the board approves them. I don't send anything.

## The steps

| # | Step | What happens | Read |
|---|---|---|---|
| 1 | Setup | Body, date, attendees (from the user), quorum rule from the bylaws if provided. Ask: **did the notes come from a recording or auto-transcript?** If so, remind the user to confirm everyone consented to recording. Rules differ by place: tell them to check, and don't state the law | `references/minutes-form.md` §4 |
| 2 | Privacy gate | Flag Red content (health, client cases) for exclusion or executive session | `references/minutes-form.md` §3 |
| 3 | Structure | Parse the notes into agenda items; propose the order | |
| 4 | Extract | Motions (mover, seconder, vote, outcome), decisions, conflicts of interest, executive session (times and topic only), action items | `references/minutes-form.md` §2 |
| 5 | Resolve | Show every `[CONFIRM]` grouped and numbered; the user settles them | |
| 6 | Draft minutes | Fill `assets/minutes-template.md` | `references/minutes-form.md` §1 |
| 7 | Lint | `minutes.py lint draft.md`; fix every error; list remaining `[CONFIRM]` | |
| 8 | Action tracker | `init` once per body, then `add` each action after confirming owner and date | `references/actions-and-follow-up.md` |
| 9 | Follow-up | `digest` → draft reminder messages per owner, for the user to review and send | `references/actions-and-follow-up.md` §3 |

## Scripts

`scripts/minutes.py`: one file, standard library only. Exit codes: `0` ok, `1` lint errors or overdue actions, `2` bad input.

| Subcommand | Use it for |
|---|---|
| `lint` | Quorum, call-to-order and adjournment times, attendance, each motion's mover, seconder and outcome, vote tallies that add up to members present, a conflict declaration for every recusal, no discussion in executive session, unresolved `[CONFIRM]`, DRAFT banner until approval |
| `init` | Create the tracker with the body's member list |
| `add` | Add an action: owner must be a named member (not "the board"); due date absolute, or `--due-in-days N --anchor DATE` after the user confirms the anchor |
| `list` | Open actions; `--owner`, `--overdue`, `--all` |
| `close` | Close an action with a note |
| `digest` | Open actions by owner, overdue first: the basis for reminder drafts |
| `export-csv` | All actions as CSV |

## Connectors

None needed. With a calendar or email connector, you may **draft** reminders there only if the user asks, and you never send without their explicit OK on the exact text. Without one, give the text to copy.

## Outputs and provenance

Draft minutes (Markdown, or Word via the docx skill), the tracker file, reminder drafts. The minutes end with:

```
Prepared from: {notes or transcript, date received} · board-minutes-tracker 0.1.0
Lint: {PASS/FAIL} · Open [CONFIRM] items: {n} · Status: DRAFT, not approved
```

## Boundaries and handoffs

- **Never** marks minutes approved, sends reminders or emails, invents votes, seconders, attendees or dates, or records executive-session discussion.
- **Not legal advice.** State nonprofit law and bylaws vary. Say what the bylaws the org provided say; send legal questions (quorum disputes, whether something needed a vote, record-keeping duties) to the org's counsel.
- **Recording consent:** remind the user to check; never state what the law requires.
- **Personnel or client matters:** recommend executive session and a general description; never put the details in the minutes.

## When this goes wrong

| Symptom | Likely cause | First fix |
|---|---|---|
| Lint: tally doesn't add up | Someone left, abstained or recused | `[CONFIRM]` the tally; record abstentions, recusals or departures |
| Lint: missing seconder | Not in the notes | `[CONFIRM: seconder not recorded]`; never pick a name |
| Owner is "the board" | Group assignment | Ask which person leads it |
| "By next meeting" | Relative date | Confirm the next meeting date, then use `--due-in-days` with that anchor, or the date itself |
| Notes include a health or HR detail | Discussion spilled over | Leave it out; suggest executive session with "Topic: personnel" |
| User asks to mark the minutes approved | Wants to close the loop | Explain approval happens at the next meeting; offer the approval line for the secretary to fill in |

## Reference files

| File | Read when |
|---|---|
| `references/minutes-form.md` | Steps 1–6: the form, motions, conflicts, executive session, Red content, recording consent |
| `references/actions-and-follow-up.md` | Steps 8–9: owners, dates, tracker, reminder drafts |
| `assets/minutes-template.md` | Drafting the minutes (step 6) |
| `assets/state-template.json` | What the tracker file holds |
