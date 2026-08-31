# AI Tool Workflow

## Primary AI tool(s) used
- **Claude** — planning, requirement analysis, architecture/spec design,
  prompt authoring, documentation, and reviewing outputs. Used for
  everything that doesn't require actually executing/generating code
  inside the repo.
- **Cursor** — code generation only, inside the actual repo, one task at a
  time. Kept deliberately narrow in scope because of an org-wide $70/month
  usage cap — every Cursor session needs to count.

The two aren't interchangeable in this workflow: Claude does the thinking,
Cursor does the typing. This split exists for a cost reason as much as a
quality reason — Claude iteration is free, Cursor iteration isn't.

## How I provide project context to the tool
- A `.cursorrules` file at the repo root, auto-loaded by Cursor for every
  session, encodes the standing rules (layer boundaries, naming
  conventions, what not to build) so they don't need repeating per prompt.
- A `project-context.md` (schema, row counts, exact quality-issue counts,
  required checks/aggregations) and `spec.md` (architecture, per-script
  responsibilities) are written once, ahead of any code generation, and
  referenced by section from every task prompt rather than re-explained.
- Each Cursor prompt is self-contained enough to run as a single session:
  it states the target file, the relevant schema, acceptance criteria, and
  explicit boundaries (e.g. "no cleaning logic — that's Silver's job").

## How I use AI for requirement analysis
The exercise brief itself was read and broken down with Claude first:
identifying the three graded parts and their weights, the five Core
components and their dependency order, the exact required repo structure,
and which of the "Common Technical Requirements" checklist items are
non-negotiable vs where there's design freedom (e.g. exact type-validation
rule choices). This became `requirements-analysis.md` and directly shaped
the task order in `task-breakdown.md` — data generation before Bronze,
Bronze before Silver, Silver before Gold, since each layer's prompt
depends on the previous layer's actual output schema.

## How I use AI for pipeline design (Bronze/Silver/Gold)
Layer boundaries were defined *before* any code was requested: Bronze =
raw ingest only, Silver = validate-and-flag (never delete), Gold =
aggregate only from validated data. This was written into both
`spec.md` (the "why") and `.cursorrules` (the enforced "must"), so the
boundary is structural rather than something re-negotiated per prompt.
Design questions with real trade-offs (e.g. which rows feed Gold — only
passed rows, or all rows with a flag column carried through) are resolved
in `design-notes.md` before the corresponding Cursor prompt is written,
not decided ad hoc by whatever Cursor generates first.

## How I use AI for code generation (Python/PySpark/SQL)
One task, one prompt, one Cursor session — never an open-ended chat. Each
prompt embeds the exact schema, exact row/issue counts, exact output
filename, and the acceptance criteria it needs to satisfy, so the goal is
a correct result on the first pass rather than iterative refinement inside
Cursor. Refinement happens in Claude beforehand (getting the prompt right)
rather than in Cursor after (fixing wrong code), because only the latter
costs against the usage cap.

## How I validate AI-generated code and logic
- Row-count and logic checks against the spec: e.g. Silver's completeness
  check should flag ~50 NULL emails and ~100/~200 NULL customer_id/
  product_id in orders — if the flagged count doesn't match the known
  injected count, that's a bug, not a data surprise.
- Manual read-through against `.cursorrules` layer boundaries (did Bronze
  code sneak in a `.dropna()` or filter — a common failure mode).
- Local execution (Databricks Community Edition / local PySpark) before
  anything is marked accepted in `task-breakdown.md`.

## How I use AI for testing and validation
Data-quality tests assert the pipeline actually catches what was
intentionally injected — e.g. asserting the completeness check flags
exactly the ~50 rows seeded with NULL email, not "some rows." Pipeline
integration tests run Bronze → Silver → Gold end-to-end against the
sample data and check it completes without error and produces the
expected table shapes. Test design happens with Claude; test code
generation is its own scoped Cursor prompt.

## How I use AI for debugging
Failures are diagnosed with Claude first — is this a logic error, a
misunderstanding of the schema, or an actual code bug — before deciding
whether it needs a fix-prompt back to Cursor at all. If it does, the
fix-prompt is targeted (describe exactly what's wrong and what's
expected) rather than "here's an error, fix it," to avoid burning a full
session re-explaining context Cursor should already have via
`.cursorrules`/`project-context.md`. Each debugging exchange is logged in
`debugging-notes.md` and `ai-prompts/debugging.md`, including the root
cause, not just the fix.

## How I use AI for data quality checks
The four required checks (completeness, uniqueness, referential
integrity, and a business-logic/type-validation check) are specified with
their exact target columns and flagging behavior in `spec.md` before any
prompt is written, and the sample data's known injected-issue counts
(from the brief) act as the ground truth to validate the checks against —
if a check's flagged count doesn't match, the check is wrong.

## What information I avoid sharing unnecessarily with AI tools
- No real customer PII, ever — all data here is synthetically generated
  specifically to avoid this question, since the exercise brief calls for
  a sample-data generator rather than real records.
- No production credentials, connection strings, internal hostnames, or
  Vault secret paths, even example-shaped ones — prompts reference
  configuration via placeholders/variable names, not real values.
- No internal-only business context beyond what's needed for the task at
  hand (e.g. real revenue figures, real customer segment definitions from
  other systems) — kept to what's in the public exercise brief.

## How I would reuse this workflow in a real production pipeline
The core discipline transfers directly: separate the thinking tool from
the execution tool, write the spec and standing rules before touching
code generation, keep every code-gen session scoped to one task with
explicit acceptance criteria, and validate against known-good expectations
rather than "it ran without error." In production the standing-rules file
would also encode real constraints this exercise doesn't have — actual
data contracts, actual PII handling policy, actual on-call/rollback
expectations — but the shape (context once, scoped prompts, validate
against ground truth, log the trail) is the same regardless of scale.

## Lessons learned: what worked, what didn't
**What worked:** front-loading `.cursorrules`/`project-context.md`/
`spec.md` before any code generation meant later prompts stayed short —
they could reference a section instead of re-explaining the whole system.
Treating the data's known intentional-issue counts as ground truth made
validating Silver's checks unambiguous instead of a judgment call.

**What didn't (to be updated as we hit real friction during Part B):**
this section will be filled in with concrete examples as components are
actually built — e.g. any case where a prompt looked complete but still
needed a fix-iteration, and what was missing from it.
