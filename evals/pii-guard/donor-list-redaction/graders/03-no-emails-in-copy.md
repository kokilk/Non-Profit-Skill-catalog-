---
type: regex
target: { source: file, path: donors-redacted.csv }
pattern: '@example\.(org|com|net)'
flags: i
match: not_contains
---
