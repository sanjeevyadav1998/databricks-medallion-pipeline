# Design Notes

Decisions made before code generation, with reasoning — so Cursor prompts
can reference a decision instead of re-litigating it, and so a reviewer
can see the "why" behind each choice.

## Decision: DBFS, not real AWS S3
**Options considered:** real S3 bucket with IAM credentials, vs DBFS
(Databricks' built-in file store).
**Chosen:** DBFS.
**Why:** the brief says "S3/DBFS" — both are explicitly acceptable. Real
S3 would require an AWS account, IAM role/keys, and bucket setup with zero
benefit to what's being evaluated (the pipeline logic, not cloud
plumbing). DBFS is already available for free in Databricks Free Edition
with no extra setup.
**Trade-off accepted:** if this were a real production system, the S3
path would matter for cost/access-control reasons. Noted here as a
scoped-exercise simplification, not something forgotten.

## Decision: Silver's 4 checks — what the "4th" check is
**Problem:** the brief names 3 check categories explicitly (completeness,
uniqueness, referential integrity) but the required repo structure has 5
numbered Silver scripts (01–05), and elsewhere refers to "all 4 quality
checks."
**Chosen resolution:** treat `03_quality_type_validation.py` (format/type
checks — e.g. valid email format, valid date ranges) as one of the named
checks, and `05_quality_business_logic.py` (domain rules, e.g.
`total_amount ≈ quantity × unit_price`) as an additional check beyond the
literal "4," since it's structurally required by the repo layout even if
not separately counted in the prose.
**Why:** favors satisfying the concrete repo-structure requirement (which
is unambiguous) over guessing at which prose number is authoritative.
Flagged in `requirements-analysis.md` as worth re-confirming if
clarification becomes available.

## Decision: Gold reads only Silver-passed rows by default
**Options considered:** (a) Gold aggregates only rows that passed all
Silver checks, (b) Gold aggregates all rows regardless of flag, with the
flag carried through for downstream filtering.
**Chosen:** (a), passed-rows-only, as the default — with each Gold SQL
script able to override this explicitly if a specific aggregation calls
for it (e.g. an analytics need to see revenue *including* flagged orders).
**Why:** the brief describes Gold as "business-ready aggregations" built
on Silver's *validated* data — flagged rows are, by definition, not yet
validated. Business dashboards showing revenue numbers should not
silently include rows known to have referential-integrity problems (e.g.
an order pointing at a non-existent product).
**Trade-off accepted:** this could under-count real revenue if some
flagged rows are actually fine (e.g. a false-positive flag). Acceptable
for this exercise; in production this would be a real conversation with
data quality's owning team about false-positive tolerance.

## Decision: Bronze does zero transformation, including type coercion beyond read-time necessity
**Why:** the brief is explicit — "No transformations or cleaning — just
raw ingest." This is stated directly (not inferred), so it's encoded as a
hard rule in `.cursorrules` rather than left as a design note alone,
since it's the boundary most likely to get blurred by default
code-generation behavior (a natural instinct is to "clean while you're at
it").

## Decision: one Cursor prompt = one repo task, never a multi-task prompt
**Options considered:** batch multiple related scripts into one large
Cursor prompt (e.g. all 3 Bronze ingestion scripts in one shot) vs one
prompt per script.
**Chosen:** batch same-layer scripts that share a schema pattern (e.g. the
3 Bronze ingestion scripts can reasonably go in one session since they're
structurally identical), but never mix layers in one prompt.
**Why:** balances the $70/month cost constraint (fewer total sessions)
against the risk of one bloated prompt producing subtly wrong code across
multiple files that's harder to review carefully. Layer-crossing is never
batched because that's exactly where boundary violations (Bronze doing
Silver's job) are most likely to slip through unnoticed in a big diff.

## Open question, not yet decided
Whether to attempt the optional Stretch tier at all. Deferred until Core
is fully built and validated — attempting Stretch before Core artifacts
are solid would risk exactly what the brief warns against (pipeline
complexity growing at the expense of the lifecycle artifacts that are
actually weighted higher).
