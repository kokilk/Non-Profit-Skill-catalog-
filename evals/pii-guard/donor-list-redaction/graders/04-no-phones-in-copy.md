---
type: regex
target: { source: file, path: donors-redacted.csv }
pattern: '555[\s.-]?01\d\d'
flags: i
match: not_contains
---
