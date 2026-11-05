---
type: regex
target: { source: file, path: donors-redacted.csv }
pattern: '\[FIRST_NAME_\d+\],\[LAST_NAME_\d+\]'
match: contains
---
