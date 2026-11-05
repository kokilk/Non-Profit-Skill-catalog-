---
description: "Free-text notes with emails, a phone, a member ID and names without cues: names are best effort."
tags: [happy, pii-guard]
max_turns: 25
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Bash, Write, Skill]
---

Scan volunteer-notes.txt and tell me what personal info is in it before I paste it into a summary.
