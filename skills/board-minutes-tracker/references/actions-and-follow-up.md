# Actions and follow-up

Read this at steps 8–9: adding actions to the tracker and drafting reminders.

## 1. Owners

Every action needs **one named person** from the member list. "The board", "staff" or "everyone" isn't an owner: ask who leads it. If the owner isn't a member (a staff member, say), ask whether to add them to the tracker's list with `init` on a new tracker, or note them in the action text with a member as the accountable owner.

## 2. Due dates

Dates are absolute: `--due 2026-11-15`. Relative dates ("by next meeting", "in two weeks", "end of quarter") become dates only after the user confirms the anchor:

> "By next meeting": is that Wednesday 18 November 2026?

Then use the date, or `--due-in-days N --anchor YYYY-MM-DD` so the script does the counting. Never pick the anchor yourself.

## 3. Reminder drafts

Run `minutes.py digest tracker.json` and draft one short message per owner: their open items, overdue first, each with its due date and the meeting it came from. Keep the tone neutral (no blame for overdue items). Show the drafts; the user sends them. **You never send.** After the user confirms an item is done, `close` it with a note.
