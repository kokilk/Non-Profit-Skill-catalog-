# Nonprofit Skill Pack: User Guide

A step-by-step guide to installing and using the five skills in **Claude chat** (claude.ai or the Claude app) and **Cowork**. No coding needed.

Menu names in this guide come from Claude's help pages as of 5 November 2026. Claude's screens change from time to time, so if a name differs slightly, look for the closest match.

## Contents
1. What this is
2. What you need before you start
3. Get the skill files
4. Install the skills in Claude chat
5. Use the skills in Cowork
6. Your first conversation
7. The five skills, one by one
8. Files you keep (and one you never upload)
9. The privacy rules in one minute
10. If something goes wrong
11. Checking the skills yourself (evals)

---

## 1. What this is

A **skill** is a small package of instructions (and sometimes a small script) that teaches Claude to do one job the same careful way every time. Once a skill is installed and turned on, Claude uses it automatically when your request matches. You don't have to call it by name.

This pack has five skills for the everyday work of a small nonprofit:

| Skill | What it does for you |
|---|---|
| **pii-guard** | Checks a file or text for personal details (emails, phone numbers, card numbers, birth dates, addresses, names, and sensitive topics like health or immigration) and makes a cleaned-up copy. Stops if the data is too sensitive to use. |
| **grant-scout** | Builds a profile of your organization, finds grants, checks eligibility against each funder's own web page, ranks them, tracks deadlines, and drafts a letter of inquiry. |
| **impact-report-builder** | Turns your program spreadsheet into a funder report where every number is calculated, not guessed. |
| **board-minutes-tracker** | Turns meeting notes or a transcript into draft minutes and a list of who's doing what by when. |
| **donor-thank-you-writer** | Drafts personal thank-you letters in your organization's voice from a gift list, checking every name and amount. |

**Every skill drafts. You decide, approve and send.** None of them sends an email, submits an application or posts anything.

## 2. What you need before you start

- **A Claude account.** Skills work on the Free, Pro, Max, Ultra, Team and Enterprise plans.
- **Code execution turned on**, because the skills run small checking scripts:
  - **Free, Pro, Max or Ultra:** open **Settings → Capabilities** and turn on **"Code execution and file creation"** (it may be labeled **"Create and edit files"**).
  - **Team or Enterprise:** an admin opens **Organization settings → Plugins & skills → Policy** and makes sure **"Cloud code execution and file creation"** and **"Skills"** are on. On Team plans they're on by default.
- **The five skill files** (next section).
- **About 10 minutes.**

## 3. Get the skill files

The skills are five `.zip` files:

```
pii-guard.zip
grant-scout.zip
impact-report-builder.zip
board-minutes-tracker.zip
donor-thank-you-writer.zip
```

- **If someone sent you the files,** save them in a folder you can find, for example `Documents/Claude skills`.
- **If you have the whole pack folder,** they're in its `dist/` folder.
- **If `dist/` is empty,** the person who looks after the pack runs one command from the pack folder: `python3 tools/package_skills.py`.

**Don't unzip them.** Claude wants the `.zip` as it is.

## 4. Install the skills in Claude chat

Do this once per skill. **Start with pii-guard**, because the other skills send you to it when a file names people.

1. Go to **claude.ai** (or open the Claude app) and sign in.
2. Open **Customize** and go to **Skills**.
3. Click the **"+"** button.
4. Choose **"+ Create skill"**.
5. Choose **"Upload a skill"**.
6. Select `pii-guard.zip` and confirm.
7. The skill appears in your list. Make sure its **switch is on**.
8. Repeat steps 3–7 for the other four `.zip` files.

**To check it worked:** start a new chat and type *"What can pii-guard do?"* Claude should describe it.

**To turn a skill off:** use its switch in **Customize → Skills**. **To delete one:** open it, switch it off, click **"…"** and choose **"Delete"**.

**On a Team or Enterprise plan:** skills you upload are private to you until you share them. Sharing settings depend on your admin.

## 5. Use the skills in Cowork

Skills also work in Cowork.

1. Open Cowork.
2. Click **Customize** in the left sidebar and check that the five skills are listed and switched on. Skills you uploaded in chat should already be there. If an admin added them to your organization's directory instead, click **"+"**, open the **Skills** tab and click **Install** next to each one.
3. Choose the folder you're working in (for example a folder with your grant files). Cowork can read and save files there directly, so you don't need to upload them.

**A Cowork tip for privacy:** with pii-guard, Cowork can check a file in your folder **before** Claude reads its contents. Say so up front: *"Before you read donors.csv, run pii-guard on it."*

## 6. Your first conversation

You don't need special commands. Just say what you need in plain words. Claude picks the right skill.

1. Start a **new chat** (or a new Cowork task).
2. Say what you want, for example: *"Help me find grants for our after-school reading program."*
3. Claude replies with a short introduction to what the skill can do and what it needs, then asks its first question.
4. Answer one question at a time. Each reply starts with a progress line like `Step 2 of 9 · Search plan` and ends with `Next: …`, so you always know where you are.
5. When Claude gives you a **state file** (a `.json` download), **save it**. Next time, attach it and say *"Let's continue."*

If Claude doesn't use a skill, name it: *"Use grant-scout for this."*

## 7. The five skills, one by one

Each section covers what to bring, how to start, what you get, and what the skill won't do.

### pii-guard: the privacy check (use it first)

- **Bring:** a spreadsheet (saved as CSV) or text that names people. If you have a list of client, donor or staff names, bring that too as a plain text file, one name per line: it makes name-catching much more reliable.
- **Start with:** *"Check donors.csv for personal information before I use it."*
- **You get:**
  - a summary of what was found, shown masked (like `j***@example.org`)
  - a **redacted copy** where details are replaced with tokens like `[EMAIL_1]`
  - a **mapping file** that can put the details back
- **It won't:** process "Red" data (see section 9), call anything "anonymized" or "safe", or give legal advice.
- **Important:** it protects your data fully only if the check runs **before** you upload the file. In plain chat, an uploaded file has already been shared. In Cowork, ask it to check the file before reading it.

### grant-scout: find and track grants

- **Bring:** basic facts about your organization:
  - tax status (for example 501(c)(3))
  - where you work, and your annual budget
  - what you want funded and roughly how much
  - whether you're registered in SAM.gov (needed for federal grants)
- **Start with:** *"Help me find grants for our literacy program in Franklin County, Ohio."*
- **You get:**
  - a ranked list: each grant's score comes with its reasons, and ineligible grants are listed with why
  - questions to answer where eligibility isn't clear
  - a deadline schedule that counts back from each due date
  - a draft **letter of inquiry** with a table showing where every fact came from
- **It won't:** list a grant as open unless it opened the funder's own page; guess a deadline; submit anything; or write a full proposal.

### impact-report-builder: the funder report

- **Bring:** your program data as a **CSV**. In Excel, use **File → Save As → CSV UTF-8**. Also bring who the report is for, the reporting period, and the results the funder asked about.
- **Start with:** *"Build a spring impact report for our funder from program-data.csv."*
- **You get:**
  - a check of your data (duplicates, blanks, unclear dates)
  - plain-language definitions of each metric, for you to approve
  - calculated results, with groups under 5 people hidden to protect privacy
  - a draft report in which every number has been checked against the calculation
- **It won't:** invent outcomes ("70% improved"), claim your program *caused* a change, or use client case notes.

### board-minutes-tracker: minutes and action items

- **Bring:** your meeting notes or transcript, who attended, and your quorum rule (if your bylaws define one).
- **Start with:** *"Turn these board meeting notes into draft minutes."* Then paste the notes, or attach the file.
- **You get:**
  - draft minutes in standard form: motions, votes, decisions
  - a list of anything unclear to confirm (for example "who seconded?")
  - an action tracker with a named owner and a real date for each item
  - reminder messages, as drafts for you to send
- **It won't:** guess a vote or a seconder, mark minutes approved (your board does that), record executive-session discussion, or send reminders.
- **If your notes came from a recording,** it will remind you to confirm everyone agreed to being recorded.

### donor-thank-you-writer: thank-you letters

- **Bring:**
  - 2–3 thank-you letters you like (for your voice)
  - a few **true, current impact facts** (for example *"Our tutors met with 312 students this year"*)
  - your gift list as a CSV: gift ID, donor ID, first name, last name, gift date (YYYY-MM-DD), amount
- **Start with:** *"Draft thank-you letters for this month's gifts in gifts.csv."*
- **You get:**
  - a check of the gift list (duplicates, refunds, anonymous donors, gifts in honor or in memory of someone)
  - one letter per donor, each checked for the right name, amount and date, plus the acknowledgment wording gifts of $250 or more need
  - a merge-ready file for you to send
- **First time:** it will ask you to set your **major-gift amount** and when a donor counts as **lapsed**. It never assumes these.
- **It won't:** send anything, give tax advice, or use any impact claim you didn't supply. Check the acknowledgment rules with your accountant.

## 8. Files you keep (and one you never upload)

| File | What it is | What to do with it |
|---|---|---|
| `grant-pipeline-….json`, `impact-report-….json`, `action-tracker-….json`, `thank-you-….json`, `pii-guard-….json` | The skill's memory of your work so far | Save it. Attach it next time to continue. Share it only with co-workers on the same task |
| Redacted copy (from pii-guard) | Your file with personal details replaced by tokens | Use this one with the other skills. Still look through it before sharing |
| **Mapping file** (from pii-guard) | The key that turns tokens back into real details | **Keep it on your own computer. Never upload it to any chat.** Delete it when you're done |

## 9. The privacy rules in one minute

| Tier | Examples | Rule |
|---|---|---|
| 🟢 **Green** | Public information, totals, your mission text | Fine to use |
| 🟡 **Amber** | Donor names and amounts, staff names, board minutes, internal finances | OK with care. Run pii-guard first for lists of people. Check your organization's own rules for using AI tools |
| 🔴 **Red** | Client case notes, health or mental health, immigration status, shelter locations, children's details, card or account numbers, criminal history | **Don't use with the skills.** Make a summary with counts only, instead |

**Remember: uploading a file to a chat sends it to the model.** Check lists of people *before* you upload them.

## 10. If something goes wrong

| What you see | What to do |
|---|---|
| Upload fails | Check the file is the `.zip` and not unzipped. One Claude help page says a skill's description can be at most 200 characters, and these skills' descriptions are about 430–460 characters. If the upload is rejected over the description, tell whoever looks after the pack: they can shorten the descriptions and rebuild |
| Skills look greyed out | Code execution is off: see section 2 |
| Claude doesn't use the skill | Check it's switched on in **Customize → Skills**, then name it in your request |
| "Not UTF-8" or "expected a .csv" | In Excel: **File → Save As → CSV UTF-8**, then upload again |
| pii-guard says "Redaction refused" | The file has Red data. That's the rule working. Remove those columns, or use totals instead |
| A grant shows as an "unverified lead" | Nobody has opened the funder's own page yet. Ask Claude to open it, or paste the page text |
| A number in your report fails the check | Use the number from the calculated results. Don't retype it |
| Minutes show `[CONFIRM: …]` | The notes didn't say. Answer the question; don't guess |
| The letter writer won't segment donors | Tell it your major-gift amount and lapsed period |
| You want something sent or submitted | The skills never send. You'll get the text or a merge-ready file to send yourself |

Problems that keep happening: tell the pack's owner (see `docs/RUNBOOK.md`, "Who to call").

## 11. Checking the skills yourself (evals)

The pack comes with **46 test cases** that show whether each skill behaves as it should, for example that it refuses to invent a grant. You can run them by hand in Claude chat with **`docs/EVAL-RUN-SHEET.md`**. Each case gives you the prompt to paste, the files to attach, and the checks to tick, once with the skill **on** and once with it **off**.

---

**Sources for the install steps:**
- [Use skills in Claude](https://support.claude.com/en/articles/12512180-use-skills-in-claude)
- [How to create custom skills](https://support.claude.com/en/articles/12512198-how-to-create-custom-skills)
