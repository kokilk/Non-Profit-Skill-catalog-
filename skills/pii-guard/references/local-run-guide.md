# Running the scanner on your own computer

Read this for Mode A (the file is still only on the user's computer), and at steps 4 and 7. Walk the user through it one step at a time; they may never have opened a terminal. Keep each instruction to one action and wait for "done" before the next.

## Contents
1. What you need
2. Get the script
3. Open a terminal in the right folder
4. Scan, redact, verify
5. Restore names into a finished draft
6. Where to keep the mapping file
7. If something goes wrong

## 1. What you need

- The one file `scan.py`. Nothing to install apart from Python.
- **Python 3.9 or newer.** Check:
  - **Mac:** open Terminal (press Cmd+Space, type `Terminal`, press Return), type `python3 --version` and press Return. You should see `Python 3.9` or higher. If you see a prompt to install developer tools, accept it and try again.
  - **Windows:** open the Start menu, type `cmd`, press Return, then type `py --version`. If it says the command isn't found, install Python from python.org (tick **"Add python.exe to PATH"** on the first screen), then open a new Command Prompt.

## 2. Get the script

Put `scan.py` and the file to check **in the same private folder**, for example a new folder called `privacy-check` in your Documents. Not on a shared drive, and not in a folder that syncs to the cloud if you can avoid it.

## 3. Open a terminal in the right folder

- **Mac:** in Terminal, type `cd ` (with a space), drag the `privacy-check` folder from Finder onto the Terminal window, then press Return.
- **Windows:** open the `privacy-check` folder in File Explorer, click the address bar, type `cmd` and press Return. A black window opens already in that folder.

What you'll see (text version of the screen):

```
privacy-check % _          ← Mac: the folder name, then a blinking cursor
C:\Users\you\Documents\privacy-check>_     ← Windows
```

On Windows, write `py` wherever these steps say `python3`.

## 4. Scan, redact, verify

**Scan.** Replace `donors.csv` with your file's name:

```
python3 scan.py scan donors.csv
```

You'll see a summary with counts, columns and masked examples like `j***@example.org`. It never shows full values. If you have a list of names (clients, donors, staff), save it as `names.txt` with one full name per line and add `--names names.txt`.

**Redact.** Choose a private place for the mapping file first (see §6). Then:

```
python3 scan.py redact donors.csv --out donors-redacted.csv --map private/donors-map.json --mask-columns first_name,last_name
```

- `--out` is the new, redacted copy. Your original file isn't changed.
- `--map` is the mapping file: it can turn the tokens back into real values. **Never upload it.**
- `--drop-columns notes` removes a column completely, which is better than masking when the column isn't needed.
- If it says **"Redaction refused: this file contains Red data"**, stop and come back to the chat. Don't look for a way around it.

**Verify.**

```
python3 scan.py verify donors-redacted.csv
```

`PASS` means no recognized identifiers are left. Still open the redacted copy and look through it before you upload it: the scanner can miss names and unusual formats.

**Then** upload only `donors-redacted.csv`.

## 5. Restore names into a finished draft

When a report or letter drafted from the redacted copy is final, save the draft (for example `thank-you-draft.md`) into the same folder, then:

```
python3 scan.py restore thank-you-draft.md --map private/donors-map.json --out private/thank-you-final.md
```

The finished file holds real names and details again, so keep it local like the mapping file. Don't paste it back into the chat.

## 6. Where to keep the mapping file

- **Good:** a private folder on your own computer, such as `privacy-check/private/`.
- **Not:** Dropbox, OneDrive, Google Drive, iCloud Drive, Box, a shared network drive, or a git repository. The script refuses the obvious ones.
- On Mac and Linux the script makes the mapping file readable only by you. On Windows, file permissions work differently, so keep it in your own user folder.
- **When the work is done,** delete the mapping file if you won't need to restore anything again.

## 7. If something goes wrong

| You see | Do this |
|---|---|
| `command not found: python3` | Mac: accept the developer tools prompt. Windows: use `py` instead |
| `error: file not found` | Check the file name and that you're in the right folder (`ls` on Mac, `dir` on Windows lists files) |
| `unsupported file type '.xlsx'` | In Excel: File → Save As → CSV UTF-8. Then scan the CSV |
| `not UTF-8 text` | Re-save as "CSV UTF-8" (Excel) or "UTF-8" (text editors) |
| `refusing to write the mapping file … synced folder` | Pick a folder from §6 |
| `already exists` | Choose a new `--out` name, or add `--overwrite` if you're sure |
