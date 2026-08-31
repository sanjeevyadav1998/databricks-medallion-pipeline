# Cursor Rules / Instructions Used

The actual enforced rules live in `.cursorrules` at the repo root (Cursor
picks this up automatically for every session in this repo). This file
documents *why* those rules exist, for the submission.

## Why these rules
- **Layer boundaries** (Bronze/Silver/Gold responsibilities) are the most
  common way generated pipeline code drifts from a medallion design — a
  model asked for "ingestion" will often sneak in cleaning logic unless
  explicitly told not to. Stating it once in `.cursorrules` means it doesn't
  need to be repeated in every prompt.
- **Naming conventions** are enforced up front because the submission is
  graded partly on matching the required repo structure exactly — letting
  Cursor freelance filenames would create rework.
- **`# ASSUMPTION:` comment convention** exists so silent guesses are
  visible during review, which is exactly what "validation" in the doc's
  Cursor expectations is asking to see evidence of.
- **Out-of-scope list** exists because the exercise doc explicitly warns
  against expanding pipeline complexity at the expense of the lifecycle
  artifacts — this keeps Cursor from over-building.

See `.cursorrules` at the repo root for the enforced text.
